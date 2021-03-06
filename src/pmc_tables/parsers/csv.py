import logging
from pathlib import Path
from typing import List, Tuple

import pandas as pd

import pmc_tables.errors

from ._common import parser

logger = logging.getLogger(__name__)


@parser
def csv_parser(csv_file: Path) -> List[Tuple[str, dict, pd.DataFrame]]:
    df = None
    for sep in [',', '\t']:
        try:
            df = pd.read_csv(csv_file.as_posix(), sep=sep)
        except (UnicodeDecodeError, pd.errors.ParserError) as e:
            logger.debug("Encountered error parsing CSV file: %s", e)
            continue
        if len(df.columns) > 1:
            break
    if df is None:
        raise pmc_tables.errors.ParserError(f"Could not parse file: {csv_file}.")
    data = [(f"/{csv_file.name}/sheet_0", {'label': None}, df)]
    return data
