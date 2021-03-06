"""
XML Table Parser
----------------

Extract tables found in PubMed Central XML files.
"""
import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, NamedTuple, Tuple

import pandas as pd

import pmc_tables
from pmc_tables.utils import compress_to_b85

from ._common import parser
from ._pandas.io.html import read_html

logger = logging.getLogger(__name__)


class TableWrapRow(NamedTuple):
    id_: str
    label: str
    caption: str
    footer: str
    orientation: str


def read_xml(table: bytes) -> pd.DataFrame:
    table_df = read_html(table)
    assert len(table_df) == 1
    return table_df[0]


@parser
def xml_parser(xml_file: Path) -> List[Tuple[str, dict, pd.DataFrame]]:
    tree = ET.parse(xml_file.as_posix())
    table_wraps = tree.findall('.//table-wrap')
    num_tables = len(tree.findall('.//table'))

    data = []
    for table_wrap in table_wraps:
        tw_row, tables = _process_table_wrap(table_wrap)
        for i, table in enumerate(tables):
            table_bytes = _process_table(table)
            table_df = read_xml(table_bytes)
            data.append(
                (f"/{xml_file.name}/{tw_row.id_}-{i}",
                 {**tw_row._asdict(),
                  'table_html': compress_to_b85(table_bytes).decode('ascii')},
                 table_df,
            ))
    if len(data) != num_tables:
        raise pmc_tables.errors.ParserError(  # type: ignore
            "Number of data points is different than the number of tables."
            f"({len(data)} != {num_tables})")
    return data


def _process_table_wrap(table_wrap: ET.Element) -> Tuple[TableWrapRow, List[ET.Element]]:
    """
    To do:
        - Figure out what `alternatives`, `graphic`, `object-id` stands for.
    """
    # Id
    id_ = table_wrap.get('id')
    assert id_ is not None
    # Orientation
    orientation = table_wrap.get('orientation')
    orientation_text = orientation if orientation else ""
    assert isinstance(orientation_text, str)
    # Attrib
    attrib_set = set(table_wrap.attrib) - {'id', 'position', 'orientation'}
    if attrib_set:
        logger.warning("Unexpected table-wrap `attrib_set`: %s", attrib_set)
    # Label
    label = table_wrap.find('label')
    label_text = label.text if label is not None else ""
    # Caption
    caption = table_wrap.find('caption')
    caption_text = caption_to_string(caption)
    # Tables
    tables = table_wrap.findall('table')
    # Footer
    footer = table_wrap.find('table-wrap-foot')
    footer_text = caption_to_string(footer)
    # Other children
    children_set = {e.tag for e in table_wrap.getchildren()}
    children_set -= {'label', 'caption', 'table', 'table-wrap-foot'}
    if children_set:
        logger.warning("Unexpected table-wrap `children_set`: %s", children_set)
    # Return
    return TableWrapRow(id_, label_text, caption_text, footer_text, orientation_text), tables


def caption_to_string(element: ET.Element) -> str:
    if element is None:
        return ""
    element_text = ET.tostring(element, encoding='utf8', method='text').decode('utf-8')
    element_text = element_text.strip().replace('\n', ' ')
    element_text = re.sub(' +', ' ', element_text)
    return element_text


def _process_table(table: ET.Element) -> bytes:
    """
    To do:
        - Figure out what `summary` tag contains.
    """
    # Attrib
    attrib_set = set(table.attrib)
    attrib_set -= {'frame', 'border', 'rules', 'style', 'width'}
    if attrib_set:
        logger.warning("Unexpected table `attrib_set`: %s", attrib_set)
    # Children
    children_set = {e.tag for e in table.getchildren()}
    children_set -= {'thead', 'tbody'}
    if children_set:
        raise pmc_tables.errors.ParserError(  # type: ignore
            f"Unexpected table `children_set`: {children_set}")
    # DataFrame
    table_bytes = ET.tostring(table)
    return table_bytes
