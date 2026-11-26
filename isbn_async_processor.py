# =====================================================
# ADVANCED ISBN METADATA ENGINE
# STRICT ISBN VALIDATION + SAFE CROSS VERIFICATION
# GOOGLE BOOKS + OPENLIBRARY
# GENERATED ISBN RECOVERY SYSTEM
# INTERNAL BINDING VERIFICATION
# FULL DASHBOARD + TIME TRACKING
# COMPLETE FINAL VERSION
# =====================================================

import asyncio
import aiohttp
import gspread
import os
import random
import re
import time
from pathlib import Path

from oauth2client.service_account import (
    ServiceAccountCredentials
)

# =====================================================
# GOOGLE SHEETS AUTH
# =====================================================

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = (
    ServiceAccountCredentials
    .from_json_keyfile_name(
        os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS",
            str(Path(__file__).with_name("credentials.json"))
        ),
        scope
    )
)

client = gspread.authorize(creds)

spreadsheet = client.open(
    "ISBN SEARCH"
)

sheet = spreadsheet.worksheet(
    "ISBN_CHECKER"
)

# =====================================================
# FORMAT COLUMNS
# =====================================================

sheet.format(
    "A:H",
    {
        "numberFormat": {
            "type": "TEXT"
        }
    }
)

# =====================================================
# GOOGLE BOOKS API KEY
# =====================================================

API_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY", "")

# =====================================================
# SETTINGS
# =====================================================

MAX_CONCURRENT_REQUESTS = 5
MAX_NEW_ROWS = 50
CHECK_INTERVAL = 5
MAX_RETRIES = 3

# =====================================================
# TIMER
# =====================================================

START_TIME = time.time()

# =====================================================
# CACHE
# =====================================================

cache = {}

# =====================================================
# CLEAN ISBN
# =====================================================

def clean_isbn(isbn):

    isbn = str(isbn)

    isbn = isbn.strip()

    isbn = isbn.replace(".0", "")
    isbn = isbn.replace("-", "")
    isbn = isbn.replace(" ", "")

    isbn = re.sub(
        r"[^0-9Xx]",
        "",
        isbn
    )

    return isbn.upper()

# =====================================================
# VALIDATE ISBN10
# =====================================================

def is_valid_isbn10(isbn):

    isbn = clean_isbn(isbn)

    if len(isbn) != 10:
        return False

    if not isbn[:9].isdigit():
        return False

    if not (
        isbn[9].isdigit()
        or isbn[9] == "X"
    ):
        return False

    total = 0

    for i in range(9):

        total += (
            int(isbn[i]) *
            (10 - i)
        )

    check_digit = isbn[9]

    if check_digit == "X":
        total += 10

    else:
        total += int(check_digit)

    return total % 11 == 0

# =====================================================
# VALIDATE ISBN13
# =====================================================

def is_valid_isbn13(isbn):

    isbn = clean_isbn(isbn)

    if len(isbn) != 13:
        return False

    if not isbn.isdigit():
        return False

    total = 0

    for i in range(12):

        digit = int(isbn[i])

        if i % 2 == 0:
            total += digit

        else:
            total += digit * 3

    calculated = (
        10 - (total % 10)
    ) % 10

    actual = int(isbn[-1])

    return calculated == actual

# =====================================================
# STRICT ISBN VALIDATION
# =====================================================

def validate_isbn(isbn):

    isbn = clean_isbn(isbn)

    if len(isbn) == 10:
        return is_valid_isbn10(isbn)

    if len(isbn) == 13:
        return is_valid_isbn13(isbn)

    return False

# =====================================================
# ISBN10 -> ISBN13
# =====================================================

def convert_isbn10_to_13(isbn10):

    isbn10 = clean_isbn(isbn10)

    if not is_valid_isbn10(isbn10):
        return ""

    core = "978" + isbn10[:-1]

    total = 0

    for i in range(12):

        digit = int(core[i])

        if i % 2 == 0:
            total += digit

        else:
            total += digit * 3

    check_digit = (
        10 - (total % 10)
    ) % 10

    return core + str(check_digit)

# =====================================================
# ISBN13 -> ISBN10
# =====================================================

def convert_isbn13_to_10(isbn13):

    isbn13 = clean_isbn(isbn13)

    if not is_valid_isbn13(isbn13):
        return ""

    if not isbn13.startswith("978"):
        return ""

    core = isbn13[3:-1]

    total = 0

    for i in range(9):

        total += (
            int(core[i]) *
            (10 - i)
        )

    remainder = total % 11

    check_value = (
        11 - remainder
    ) % 11

    if check_value == 10:
        check_digit = "X"

    else:
        check_digit = str(check_value)

    return core + check_digit

# =====================================================
# OPENLIBRARY SEARCH
# =====================================================

async def fetch_openlibrary_data(
    session,
    isbn
):

    url = (
        f"https://openlibrary.org/api/books?"
        f"bibkeys=ISBN:{isbn}"
        f"&format=json&jscmd=data"
    )

    try:

        async with session.get(
            url,
            timeout=80
        ) as response:

            data = await response.json()

            key = f"ISBN:{isbn}"

            if key not in data:
                return None

            book = data[key]

            title = str(
                book.get(
                    "title",
                    ""
                )
            ).strip()

            subtitle = str(
                book.get(
                    "subtitle",
                    ""
                )
            ).strip()

            if (
                subtitle
                and subtitle.lower()
                not in title.lower()
            ):
                title += ": " + subtitle

            authors = book.get(
                "authors",
                []
            )

            author = ", ".join([
                a["name"]
                for a in authors
                if "name" in a
            ]).strip()

            publishers = book.get(
                "publishers",
                []
            )

            publisher = ", ".join([
                p["name"]
                for p in publishers
                if "name" in p
            ]).strip()

            year = str(
                book.get(
                    "publish_date",
                    ""
                )
            ).strip()

            binding = str(
                book.get(
                    "physical_format",
                    ""
                )
            ).strip()

            identifiers = book.get(
                "identifiers",
                {}
            )

            isbn10 = ""
            isbn13 = ""

            if identifiers.get("isbn_10"):

                isbn10 = clean_isbn(
                    identifiers["isbn_10"][0]
                )

            if identifiers.get("isbn_13"):

                isbn13 = clean_isbn(
                    identifiers["isbn_13"][0]
                )

            return {

                "isbn10": isbn10,
                "isbn13": isbn13,

                "title": title,
                "author": author,

                "publisher": publisher,
                "year": year,

                "binding": binding
            }

    except Exception as e:

        print(
            f"OPENLIBRARY ERROR -> "
            f"{isbn} -> {repr(e)}"
        )

        return None

# =====================================================
# GOOGLE BOOKS SEARCH
# =====================================================

async def fetch_google_data(
    session,
    isbn
):

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    if API_KEY:
        url += f"&key={API_KEY}"

    try:

        async with session.get(
            url,
            headers=headers,
            timeout=80
        ) as response:

            data = await response.json()

        if data.get(
            "totalItems",
            0
        ) <= 0:

            return None

        volume_info = (
            data["items"][0]
            .get("volumeInfo", {})
        )

        title = str(
            volume_info.get(
                "title",
                ""
            )
        ).strip()

        subtitle = str(
            volume_info.get(
                "subtitle",
                ""
            )
        ).strip()

        if (
            subtitle
            and subtitle.lower()
            not in title.lower()
        ):
            title += ": " + subtitle

        author = ", ".join(
            volume_info.get(
                "authors",
                []
            )
        ).strip()

        publisher = str(
            volume_info.get(
                "publisher",
                ""
            )
        ).strip()

        year = str(
            volume_info.get(
                "publishedDate",
                ""
            )
        ).strip()

        binding = str(
            volume_info.get(
                "printType",
                ""
            )
        ).strip()

        identifiers = volume_info.get(
            "industryIdentifiers",
            []
        )

        isbn10 = ""
        isbn13 = ""

        for identifier in identifiers:

            id_type = identifier.get(
                "type",
                ""
            )

            id_value = clean_isbn(
                identifier.get(
                    "identifier",
                    ""
                )
            )

            if id_type == "ISBN_10":
                isbn10 = id_value

            elif id_type == "ISBN_13":
                isbn13 = id_value

        return {

            "isbn10": isbn10,
            "isbn13": isbn13,

            "title": title,
            "author": author,

            "publisher": publisher,
            "year": year,

            "binding": binding
        }

    except Exception as e:

        print(
            f"GOOGLE ERROR -> "
            f"{isbn} -> {repr(e)}"
        )

        return None

# =====================================================
# MERGE METADATA
# =====================================================

def merge_metadata(
    google_data,
    openlibrary_data
):

    final_data = {

        "isbn10": "",
        "isbn13": "",

        "title": "",
        "author": "",

        "publisher": "",
        "year": "",

        "binding": ""
    }

    if google_data:

        for key in final_data:

            if google_data.get(key):

                final_data[key] = (
                    google_data[key]
                )

    if openlibrary_data:

        for key in final_data:

            if (
                not final_data[key]
                and openlibrary_data.get(key)
            ):

                final_data[key] = (
                    openlibrary_data[key]
                )

    return final_data

# =====================================================
# FETCH BOOK
# =====================================================

async def fetch_book(
    session,
    isbn
):

    isbn = clean_isbn(isbn)

    if not validate_isbn(isbn):

        return [
            "",
            "",
            "",
            "",
            "",
            "",
            "Invalid ISBN"
        ]

    if isbn in cache:
        return cache[isbn]

    for attempt in range(MAX_RETRIES):

        try:

            await asyncio.sleep(
                random.uniform(1, 2)
            )

            google_data = await fetch_google_data(
                session,
                isbn
            )

            openlibrary_data = (
                await fetch_openlibrary_data(
                    session,
                    isbn
                )
            )

            # =================================================
            # NO METADATA FOUND
            # =================================================

            if (
                not google_data
                and not openlibrary_data
            ):

                result = [
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "No Metadata Found"
                ]

                cache[isbn] = result

                return result

            merged = merge_metadata(
                google_data,
                openlibrary_data
            )

            api_isbn10 = clean_isbn(
                merged["isbn10"]
            )

            api_isbn13 = clean_isbn(
                merged["isbn13"]
            )

            title = merged["title"]
            author = merged["author"]

            publisher = merged["publisher"]
            year = merged["year"]

            binding = merged["binding"]

            isbn10 = api_isbn10
            isbn13 = api_isbn13

            generated_status = ""

            # =================================================
            # MATHEMATICAL ISBN VERIFICATION
            # =================================================

            if len(isbn) == 13:

                generated_isbn10 = (
                    convert_isbn13_to_10(isbn)
                )

                if generated_isbn10:

                    if api_isbn10:

                        if generated_isbn10 == api_isbn10:

                            isbn10 = api_isbn10

                        else:

                            isbn10 = generated_isbn10

                            if binding:

                                generated_status = (
                                    "Edition Conflict"
                                )

                            else:

                                generated_status = (
                                    "Check ISBN10"
                                )

                    else:

                        isbn10 = generated_isbn10
                        generated_status = (
                            "Check ISBN10"
                        )

                    isbn13 = isbn

            # =================================================
            # ISBN10 INPUT
            # =================================================

            elif len(isbn) == 10:

                generated_isbn13 = (
                    convert_isbn10_to_13(isbn)
                )

                if generated_isbn13:

                    if api_isbn13:

                        if generated_isbn13 == api_isbn13:

                            isbn13 = api_isbn13

                        else:

                            isbn13 = generated_isbn13

                            if binding:

                                generated_status = (
                                    "Edition Conflict"
                                )

                            else:

                                generated_status = (
                                    "Check ISBN13"
                                )

                    else:

                        isbn13 = generated_isbn13
                        generated_status = (
                            "Check ISBN13"
                        )

                    isbn10 = isbn

            # =================================================
            # MISSING FIELDS
            # =================================================

            missing_fields = []

            if not isbn10:
                missing_fields.append(
                    "Missing ISBN10"
                )

            if not isbn13:
                missing_fields.append(
                    "Missing ISBN13"
                )

            if not title:
                missing_fields.append(
                    "Missing Title"
                )

            if not author:
                missing_fields.append(
                    "Missing Author"
                )

            if not publisher:
                missing_fields.append(
                    "Missing Publisher"
                )

            if not year:
                missing_fields.append(
                    "Missing Year"
                )

            # =================================================
            # FINAL STATUS
            # =================================================

            if generated_status:

                if missing_fields:

                    status = (
                        generated_status
                        + ", "
                        + ", ".join(
                            missing_fields
                        )
                    )

                else:

                    status = generated_status

            else:

                if not missing_fields:

                    status = "Valid"

                else:

                    status = ", ".join(
                        missing_fields
                    )

            result = [

                isbn10,
                isbn13,

                title,
                author,

                publisher,
                year,

                status
            ]

            cache[isbn] = result

            return result

        except Exception as e:

            print(
                f"RETRY ERROR -> "
                f"{isbn} -> {repr(e)}"
            )

            await asyncio.sleep(5)

    return [
        "",
        "",
        "",
        "",
        "",
        "",
        "Retry Needed"
    ]

# =====================================================
# SETUP DASHBOARD
# =====================================================

def setup_dashboard():

    dashboard = [

        ["Processed Rows", ""],
        ["Remaining Rows", ""],
        ["Current Batch", ""],
        ["Engine Status", ""],
        ["Time Taken", ""],

        ["Fully Valid", ""],
        ["Manual Review", ""],
        ["Invalid ISBN", ""],
        ["No Metadata Found", ""],

        ["Missing ISBN10", ""],
        ["Missing ISBN13", ""],
        ["Missing Title", ""],
        ["Missing Author", ""],
        ["Missing Publisher", ""],
        ["Missing Year", ""],

        ["Check ISBN10", ""],
        ["Check ISBN13", ""],
        ["Edition Conflict", ""]

    ]

    sheet.update(
        values=dashboard,
        range_name="K2:L19"
    )

# =====================================================
# PROCESS ROWS
# =====================================================

async def process_new_rows():

    connector = aiohttp.TCPConnector(
        limit=MAX_CONCURRENT_REQUESTS
    )

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:

        data = sheet.get_all_values()

        tasks = []
        row_numbers = []

        processed_rows = 0
        remaining_rows = 0

        fully_valid = 0
        manual_review = 0
        invalid_isbn = 0
        no_metadata = 0

        missing_isbn10 = 0
        missing_isbn13 = 0
        missing_title = 0
        missing_author = 0
        missing_publisher = 0
        missing_year = 0

        check_isbn10 = 0
        check_isbn13 = 0
        edition_conflict = 0

        for idx, row in enumerate(
            data[1:],
            start=2
        ):

            input_isbn = (
                row[0]
                if len(row) > 0
                else ""
            )

            status = (
                row[7]
                if len(row) > 7
                else ""
            )

            if status:

                processed_rows += 1

                if status == "Valid":
                    fully_valid += 1

                if "Invalid ISBN" in status:
                    invalid_isbn += 1

                if "No Metadata Found" in status:
                    no_metadata += 1

                if (
                    "Check" in status
                    or "Missing" in status
                    or "Conflict" in status
                ):
                    manual_review += 1

                if "Missing ISBN10" in status:
                    missing_isbn10 += 1

                if "Missing ISBN13" in status:
                    missing_isbn13 += 1

                if "Missing Title" in status:
                    missing_title += 1

                if "Missing Author" in status:
                    missing_author += 1

                if "Missing Publisher" in status:
                    missing_publisher += 1

                if "Missing Year" in status:
                    missing_year += 1

                if "Check ISBN10" in status:
                    check_isbn10 += 1

                if "Check ISBN13" in status:
                    check_isbn13 += 1

                if "Edition Conflict" in status:
                    edition_conflict += 1

            if not input_isbn:
                continue

            if (
                status
                and status != "Retry Needed"
            ):
                continue

            remaining_rows += 1

            tasks.append(
                fetch_book(
                    session,
                    input_isbn
                )
            )

            row_numbers.append(idx)

            if (
                len(tasks)
                >= MAX_NEW_ROWS
            ):
                break

        # =================================================
        # DASHBOARD STATUS
        # =================================================

        sheet.batch_update([

            {
                "range": "L2",
                "values": [[processed_rows]]
            },

            {
                "range": "L3",
                "values": [[remaining_rows]]
            },

            {
                "range": "L4",
                "values": [[len(tasks)]]
            },

            {
                "range": "L5",
                "values": [["Processing"]]
            }

        ])

        # =================================================
        # RUN TASKS
        # =================================================

        if tasks:

            results = await asyncio.gather(
                *tasks
            )

            batch_updates = []

            for row_num, result in zip(
                row_numbers,
                results
            ):

                batch_updates.append({

                    "range":
                        f"B{row_num}:H{row_num}",

                    "values":
                        [result]
                })

            sheet.batch_update(
                batch_updates
            )

        # =================================================
        # TIME TRACKING
        # =================================================

        elapsed_seconds = (
            time.time() - START_TIME
        )

        elapsed_minutes = round(
            elapsed_seconds / 60,
            2
        )

        # =================================================
        # FINAL DASHBOARD
        # =================================================

        sheet.batch_update([

            {
                "range": "L5",
                "values": [["Idle"]]
            },

            {
                "range": "L6",
                "values": [[
                    f"{elapsed_minutes} mins"
                ]]
            },

            {
                "range": "L7",
                "values": [[fully_valid]]
            },

            {
                "range": "L8",
                "values": [[manual_review]]
            },

            {
                "range": "L9",
                "values": [[invalid_isbn]]
            },

            {
                "range": "L10",
                "values": [[no_metadata]]
            },

            {
                "range": "L11",
                "values": [[missing_isbn10]]
            },

            {
                "range": "L12",
                "values": [[missing_isbn13]]
            },

            {
                "range": "L13",
                "values": [[missing_title]]
            },

            {
                "range": "L14",
                "values": [[missing_author]]
            },

            {
                "range": "L15",
                "values": [[missing_publisher]]
            },

            {
                "range": "L16",
                "values": [[missing_year]]
            },

            {
                "range": "L17",
                "values": [[check_isbn10]]
            },

            {
                "range": "L18",
                "values": [[check_isbn13]]
            },

            {
                "range": "L19",
                "values": [[edition_conflict]]
            }

        ])

# =====================================================
# MAIN LOOP
# =====================================================

async def main():

    while True:

        try:

            await process_new_rows()

        except Exception as e:

            print(
                f"MAIN LOOP ERROR -> "
                f"{repr(e)}"
            )

        await asyncio.sleep(
            CHECK_INTERVAL
        )

# =====================================================
# RUN
# =====================================================

setup_dashboard()

asyncio.run(main())
