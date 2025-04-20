# tools/finance_tools.py
import csv
import os

def read_invoices(csv_file: str):
    """
    Reads invoices from a CSV file.
    """
    invoices = []
    with open(csv_file, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            invoices.append(row)
    return invoices

def write_invoice(invoice: dict, csv_file: str):
    """
    Appends a new invoice to the CSV file.
    If the file does not exist, writes the header.
    """
    file_exists = os.path.exists(csv_file)
    fieldnames = invoice.keys()
    with open(csv_file, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(invoice)
