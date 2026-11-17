"""
Pemilih mesin posisi untuk prototipe.
  PowerShell:  $env:ASTROLIFE_ENGINE = "skyfield"     (bawaan: "lite")
Kedua mesin menyediakan antarmuka yang sama (eq, ecl, sep, topo_moon, ...), lihat ephem_lite.py.
"""
import importlib
import os

NAME = os.environ.get('ASTROLIFE_ENGINE', 'lite').strip().lower()
if NAME not in ('lite', 'skyfield'):
    raise SystemExit(f"ASTROLIFE_ENGINE='{NAME}' tidak dikenal (pilih: lite | skyfield)")
E = importlib.import_module('prototype.ephem_skyfield' if NAME == 'skyfield' else 'prototype.ephem_lite')
