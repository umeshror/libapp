import csv
import io
from typing import List, Dict, Any, Generator


def parse_csv_stream(file_stream: bytes) -> List[Dict[str, str]]:
    """
    Parses a raw byte stream from a file upload into a list of dictionaries.
    Assumes first row is header.
    """
    decoded = file_stream.decode("utf-8")
    io_string = io.StringIO(decoded)
    reader = csv.DictReader(io_string)
    return list(reader)


def generate_csv_response(data: List[Dict[str, Any]], fieldnames: List[str]) -> str:
    """
    Generates a CSV string from a list of dictionaries.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()
