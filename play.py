"""Scrape Play.fi website for available tennis / padel slots"""

import os
from time import sleep
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
import requests
import pandas as pd

pd.options.display.max_rows = 100

# GLOBALS
TODAY = datetime.today()
AVAILABLE_SLOTS = []
PARAMS = {}


def main():
    PREVIOUS_SLOTS = []
    lajit, kentät, kaupungit = get_parameters()
    venues = ask_for_user_input(lajit, kentät, kaupungit)
    selected_venue = select_venues(venues)
    fectch_and_process_data_from_url(selected_venue)
    prettify_results(filter_results())

    # TO DO:
    # Further filtering params, TIME, DAY

    pooling = input("\nPool for results upon changes?\n(Y/N): ").lower()

    if pooling == "y":

        AVAILABLE_SLOTS.clear()  # clears initial return values from 1st run

        while True:

            fectch_and_process_data_from_url(selected_venue, pooling=True)
            filttered_results = filter_results()

            if filttered_results != PREVIOUS_SLOTS and filttered_results != []:
                prettify_results(filttered_results)
            AVAILABLE_SLOTS.clear()
            PREVIOUS_SLOTS = filttered_results
            sleep(61)


def get_parameters():
    """Parses through play.fi and retrieves options used in booking calendar."""

    base_url = "https://play.fi/booking/booking-front"
    page = requests.get(base_url)
    page.raise_for_status()

    soup = BeautifulSoup(page.text, "html.parser")
    lajit = []
    for laji in soup.find_all(
        "select", attrs={"id": "facilitysearchform-search_sport_id"}
    ):
        for option in laji.find_all("option", attrs={"title": " "}):
            d = dict()
            d[option.text.lower()] = option.get("value")
            lajit.append(d)

    kentät = []
    for kenttä in soup.find_all("optgroup", attrs={"label": "Kentät ja hallit"}):
        for option in kenttä.find_all("option"):
            d = dict()
            d[option.text.lower()] = option.get("value").lower()
            kentät.append(d)

    kaupungit = []
    for kaupunki in soup.find_all("optgroup", attrs={"label": "Kaupungit"}):
        for option in kaupunki.find_all("option"):
            d = dict()
            d[option.text.lower()] = option.get("value").lower()
            kaupungit.append(d)

    return lajit, kentät, kaupungit


def ask_for_user_input(lajit: list, kentät: list, kaupungit: list) -> list:

    print("\nSelect your activity. Provide a number.")

    for idx, laji in enumerate(lajit, 1):
        print(f"\t{idx}: {list(laji.keys())[0].title()}")

    laji = input("\nActivity #: ").lower()

    clear_console()

    cities = retrieve_possible_playgrounds(laji)

    cities_filttered = []
    for d in cities:
        for k, _ in d.items():
            k = k.split(", ")[1]
            cities_filttered.append(k)

    cities_filttered = sorted(list(set(cities_filttered)))

    cities_filttered_dict = dict()
    print("\nSelect city. Provide a number.")
    for idx, kaupunki in enumerate(cities_filttered, 1):
        cities_filttered_dict[idx] = kaupunki
        print(f"\t{idx}: {kaupunki.title()}")

    kaupunki_input = int(input("\nCity #: "))
    kaupunki_selected = cities_filttered_dict[kaupunki_input].lower()

    kaupunki_value = ""
    for dic in kaupungit:
        for k, v in dic.items():
            if k == kaupunki_selected:
                kaupunki_value = v

    clear_console()
    return retrieve_possible_playgrounds(laji, kaupunki_value)


def retrieve_possible_playgrounds(laji, kaupunki=""):

    page = requests.get(
        f"https://play.fi/booking/booking-front?FacilitySearchForm%5Bsearch_sport_id%5D={laji}&FacilitySearchForm%5Bsearch_place_key%5D={kaupunki}"
    )
    page.raise_for_status()

    soup = BeautifulSoup(page.text, "html.parser")
    venues = []

    articles = soup.find_all("article")
    for article in articles:
        for div in article.find_all("div", attrs={"class": "card__info"}):
            for elem in div.find_all("a"):
                venue_name, booking_name = (
                    elem.text.strip(),
                    elem.get("href").split("/")[1],
                )
                venues.append({venue_name: booking_name})

    return venues


def validate_input(l: list):
    pass


def select_venues(venues: list) -> list:
    venue_dic = dict()
    print("\nSelect venue. Provide a number.")
    for idx, venue in enumerate(venues, 1):
        for k, v in venue.items():
            venue_dic[idx] = [k, v]
            print(f"\t{idx}: {venue}")

    venue_selected = int(input("\nVenue #: "))

    return venue_dic[venue_selected]


def filter_results(start=17, end=20):

    filttered_results = [
        slot for slot in AVAILABLE_SLOTS if start <= int(slot["Time"][:2]) <= end
    ]

    return filttered_results


def prettify_results(filttered_results):
    print("---------------------------------------------------------------------------")
    print(f"Results updated: {datetime.now().strftime('%H:%M:%S')}".center(75, " "))
    print("---------------------------------------------------------------------------")
    data = pd.DataFrame(filttered_results).reindex(
        columns=["Date", "Day", "Activity", "Place", "Time", "Court"]
    )
    data["Day"] = pd.to_datetime(data["Date"]).dt.day_name()
    print(data)


def fectch_and_process_data_from_url(venue_list: list, pooling=False) -> list:
    place = venue_list[0].replace(",", "")
    url_string = venue_list[1]

    if not pooling:
        base_url = f"https://play.fi/{url_string}/booking/booking-calendar?BookingCalForm%5Bp_laji%5D=1"

        # Fetch data using Requests
        page = requests.get(base_url)
        page.raise_for_status()

        # Parse through html using bs4
        soup = BeautifulSoup(page.text, "html.parser")
        table = soup.find("table")

        activities = (
            soup.find("div", attrs={"id": "w0", "class": "tabs__items"})
            .text.strip()
            .split()
        )

        activities_dict = dict()
        print()
        for idx, activity in enumerate(activities, 1):
            print(f"{idx}: {activity}")
            activities_dict[idx] = activity

        print("\nSelect activity according to your initial selection\n")
        activity_input = int(input("Activity #: "))
        activity = activities_dict[activity_input]

        number_of_days = 0
        number_of_days = int(
            input("\nProvide number of days to lookahead, 0 = today\n# of days: ")
        )

        PARAMS["num_of_days"] = number_of_days
        PARAMS["acitivity"] = activities_dict[activity_input]
        PARAMS["acitivity_id"] = activity_input

    for day in range(PARAMS["num_of_days"]):
        date = f"{(TODAY + timedelta(days=day)).date()}"
        url = f"https://play.fi/{url_string}/booking/booking-calendar?BookingCalForm%5Bp_laji%5D={PARAMS['acitivity_id']}&BookingCalForm%5Bp_location%5D=1&BookingCalForm%5Bp_pvm%5D={date}"

        page = requests.get(url)
        page.raise_for_status()

        # Parse through html using bs4
        soup = BeautifulSoup(page.text, "html.parser")
        table = soup.find("table")

        if table is None:
            break

        # Check if there are available slots. Returns epmty list if no results were found.
        if table.find_all("td", {"class": "s-avail"}):
            # If results:
            for td in table.find_all("td", {"class": "s-avail"}):
                for anchor in td.find_all("a", href=True):
                    court, _, beginning_time, _, _ = anchor.contents

                    AVAILABLE_SLOTS.append(
                        {
                            "Date": date,
                            "Place": place,
                            "Activity": PARAMS["acitivity"],
                            "Time": beginning_time,
                            "Court": court,
                        }
                    )


def clear_console():
    command = "clear"
    if os.name in ("nt", "dos"):  # If Machine is running on Windows, use cls
        command = "cls"
    os.system(command)


if __name__ == "__main__":
    clear_console()
    main()
