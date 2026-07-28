"""S&P 500 universe fetcher - fetches ~503 stocks instead of full 3,800+ market scan."""

import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import pandas as pd

logger = logging.getLogger(__name__)

SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# Hardcoded fallback when Wikipedia is unreachable (as of mid-2025)
_SP500_FALLBACK = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "BRK-B", "TSLA", "LLY",
    "V", "UNH", "JPM", "XOM", "MA", "AVGO", "PG", "COST", "HD", "JNJ",
    "ABBV", "MRK", "CVX", "CRM", "BAC", "WMT", "NFLX", "KO", "PEP", "TMO",
    "AMD", "ACN", "ADBE", "MCD", "ABT", "ORCL", "WFC", "LIN", "TXN", "PM",
    "DHR", "CSCO", "CAT", "IBM", "GE", "INTU", "SPGI", "AXP", "VZ", "GS",
    "UPS", "HON", "RTX", "NEE", "ISRG", "MS", "LOW", "AMGN", "T", "BKNG",
    "SYK", "BLK", "SBUX", "TJX", "ELV", "DE", "MDT", "CI", "ADI", "GILD",
    "PLD", "MDLZ", "CB", "MMM", "SO", "ZTS", "AMAT", "SCHW", "MO", "DUK",
    "NOC", "GD", "HUM", "CL", "WM", "FIS", "CSX", "USB", "ADP", "MRNA",
    "AON", "ITW", "ICE", "OXY", "TGT", "REGN", "GM", "SHW", "PNC", "EMR",
    "BSX", "MPC", "APD", "CME", "F", "CCI", "PSA", "NSC", "MCO", "VLO",
    "PYPL", "EW", "KMB", "AIG", "KLAC", "HCA", "ETN", "LRCX", "AFL", "TFC",
    "STZ", "MNST", "CTVA", "TT", "DXCM", "MMC", "D", "SLB", "BDX", "ROST",
    "PSX", "GWW", "MSCI", "PCG", "AEP", "YUM", "AME", "FTNT", "ROP", "ALL",
    "MET", "WELL", "EXC", "HSY", "PEG", "ODFL", "VRTX", "IDXX", "TEL", "OTIS",
    "CBRE", "FDX", "DLTR", "A", "KEYS", "HIG", "KR", "NUE", "IQV", "AWK",
    "XEL", "RSG", "WEC", "PPG", "PAYX", "ANSS", "FANG", "ALB", "ACGL", "ON",
    "FAST", "VRSK", "CDW", "EXPD", "CTAS", "BIIB", "DG", "MTD", "BALL", "MPWR",
    "ULTA", "CHD", "ENPH", "ARE", "PAYC", "HRL", "INCY", "IPG", "NVR", "PKG",
    "RMD", "WAT", "WST", "ALGN", "CDNS", "CPRT", "CSGP", "CTLT", "FDS", "FFIV",
    "GRMN", "HSIC", "IR", "JKHY", "MAS", "MCHP", "NTAP", "NTRS", "NXPI", "PODD",
    "POOL", "RE", "ROL", "SNPS", "STE", "SWK", "SYF", "SYY", "TRMB", "TTWO",
    "TYL", "UDR", "UHS", "URI", "WRB", "XYL", "ZBH", "BR", "EFX", "BAX",
    "BRO", "EPAM", "SEDG", "SWKS", "ZBRA", "LDOS", "TDY", "TDG", "CINF", "HOLX",
    "QRVO", "BF-B", "L", "JNPR", "LKQ", "LUV", "MGM", "MHK", "MKC", "MKTX",
    "MLM", "MOS", "NDAQ", "NRG", "NWL", "NWS", "NWSA", "O", "OMC", "PCAR",
    "PH", "PKI", "PNR", "PNW", "PPL", "PRU", "PTC", "PWR", "QCOM", "RF",
    "RJF", "RL", "ROK", "RVTY", "SEE", "SKX", "SNA", "SPG", "SWKS", "TDG",
    "TER", "TFX", "TOL", "TPR", "TROW", "TRV", "TSCO", "TSN", "UNM", "VFC",
    "VTRS", "VZ", "WAB", "WHR", "WMB", "WU", "WYNN", "XRAY", "GPC", "HAS",
    "MAS", "NI", "LNC", "IVZ", "DVN", "APA", "FSLR", "SOLV", "GEN", "SMCI",
    "DECK", "AXON", "BLDR", "NCLH", "CCL", "RCL", "DAL", "UAL", "AAL", "LMT",
    "BA", "GD", "NOC", "LHX", "TDG", "HII", "LDOS", "SAIC", "BAH", "L3H",
]


class SP500UniverseFetcher:
    """Fetches and caches the S&P 500 stock universe from Wikipedia."""

    def __init__(self, cache_dir: str = "./data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "sp500_universe.pkl"
        logger.info("SP500UniverseFetcher initialized")

    def fetch_universe(self, force_refresh: bool = False) -> List[str]:
        """Fetch S&P 500 components, with 7-day cache.

        Fetches from Wikipedia's S&P 500 list. Falls back to hardcoded list
        if Wikipedia is unreachable.

        Args:
            force_refresh: Bypass cache and fetch fresh data.

        Returns:
            List of ticker symbols in Yahoo Finance format (e.g., BRK-B).
        """
        if not force_refresh and self.cache_file.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(
                self.cache_file.stat().st_mtime
            )
            if cache_age < timedelta(days=7):
                with open(self.cache_file, 'rb') as f:
                    symbols = pickle.load(f)
                logger.info(f"Loaded {len(symbols)} S&P 500 symbols from cache")
                return symbols

        logger.info("Fetching S&P 500 components from Wikipedia...")
        try:
            tables = pd.read_html(SP500_WIKI_URL, header=0)
            df = tables[0]

            # The first table on Wikipedia's S&P 500 page has column 'Symbol'
            if 'Symbol' not in df.columns:
                raise ValueError(f"'Symbol' column not found. Columns: {df.columns.tolist()}")

            # Convert Yahoo Finance format: BRK.B → BRK-B
            symbols = (
                df['Symbol']
                .astype(str)
                .str.strip()
                .str.replace('.', '-', regex=False)
                .tolist()
            )
            symbols = [s for s in symbols if s and s != 'nan']

            logger.info(f"Fetched {len(symbols)} S&P 500 stocks from Wikipedia")

            with open(self.cache_file, 'wb') as f:
                pickle.dump(symbols, f)

            return symbols

        except Exception as e:
            logger.warning(f"Wikipedia fetch failed ({e}). Using hardcoded fallback list.")
            return list(_SP500_FALLBACK)
