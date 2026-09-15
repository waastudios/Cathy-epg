"""仅调用运营商官网或官方电视提供商页面的节目表采集器。"""

from __future__ import annotations

from datetime import date, datetime, time as clock_time, timedelta, timezone
import json
from importlib.resources import files
import re
import time
import unicodedata
from typing import Any
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import requests

from .models import Programme, utc_now_iso

USER_AGENT = "Cathy-epg/0.2 (+https://github.com/waastudios/Cathy-epg; official-source-only research tool)"
