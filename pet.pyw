"""Клодик — маленькая пиксельная версия Claude, живёт внизу экрана и умеет управлять компом.
Код — в папке klodik/. Тест: python pet.pyw --selftest"""
import os
import sys

# Библиотеки голоса лежат рядом (vendor/): так их видит и Клодик из автозапуска, а не только из папки пользователя
VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
if os.path.isdir(VENDOR):
    sys.path.insert(0, VENDOR)

from klodik.app import main  # noqa: E402

main()
