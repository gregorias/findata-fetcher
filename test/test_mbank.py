#!/usr/bin/env python
import pathlib
import unittest
from os import path

from fetcher import mbank


def testdata_dir() -> pathlib.Path:
    test_dir = pathlib.Path(path.dirname(path.realpath(__file__)))
    return test_dir / 'data'


def read_file(p: pathlib.Path, mode) -> str:
    with open(p, mode) as f:
        return f.read()


class MbankTestCase(unittest.TestCase):

    def test_preprocesses_mbanks_csv_0(self):
        raw_csv = (
            b'rubbishintro\r\n'
            b'#Data operacji;#Opis operacji;#Rachunek;#Kategoria;#Kwota;#Saldo po operacji;\r\n'
            b'2020-10-28;"\xa5CY";"eKonto 1111 1111";"Rozrywka - inne";-15,00 PLN;100,00 PLN;\r\n'
            b'\r\n'
            b'\r\n')
        expected_csv = (
            b'#Data operacji;#Opis operacji;#Rachunek;#Kategoria;#Kwota;#Saldo po operacji;\n'
            b'2020-10-28;"\xc4\x84CY";"eKonto 1111 1111";"Rozrywka - inne";-15,00 PLN;100,00 PLN;\n'
        )

        self.assertEqual(mbank.transform_and_strip_mbanks_csv(raw_csv),
                         expected_csv)

    def test_preprocesses_mbanks_csv_1(self):
        input = read_file(
            f"{testdata_dir()}/mbank-transactions-2023-04-30.csv", 'rb')
        expected = read_file(
            f"{testdata_dir()}/mbank-transactions-2023-04-30-output.csv", 'rb')

        self.assertEqual(mbank.transform_and_strip_mbanks_csv(input), expected)
