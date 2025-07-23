"""
IBKR Activity Statement CSV Parser

Parses IBKR CSV activity statements to extract transaction data for historical syncing.
This solves the issue of missing historical data from the IBKR API.
"""

import csv
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import re

logger = logging.getLogger(__name__)

class IBKRCSVParser:
    """Parser for IBKR Activity Statement CSV files"""
    
    def __init__(self):
        self.parsed_data = {
            'trades': [],
            'account_info': {},
            'dividends': [],
            'cash_transactions': []
        }
    
    def parse_csv_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse IBKR CSV activity statement file
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Dictionary containing parsed trades, dividends, and account info
        """
        logger.info(f"🔍 Parsing IBKR CSV file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                current_section = None
                
                for row in reader:
                    if not row or len(row) < 3:
                        continue
                    
                    section_type = row[0]
                    row_type = row[1]
                    
                    # Track current section
                    if row_type == 'Header':
                        current_section = section_type
                        continue
                    
                    # Parse different sections
                    if section_type == 'Account Information' and row_type == 'Data':
                        self._parse_account_info(row)
                    elif section_type == 'Trades' and row_type == 'Data' and len(row) > 10:
                        self._parse_trade(row)
                    elif section_type == 'Dividends' and row_type == 'Data':
                        self._parse_dividend(row)
                    elif section_type == 'Cash Report' and row_type == 'Data':
                        self._parse_cash_transaction(row)
            
            # Log parsing results
            logger.info(f"✅ Parsed {len(self.parsed_data['trades'])} trades")
            logger.info(f"✅ Parsed {len(self.parsed_data['dividends'])} dividends")
            logger.info(f"✅ Account: {self.parsed_data['account_info'].get('account_number', 'Unknown')}")
            
            # Sort trades by date
            self.parsed_data['trades'].sort(key=lambda x: x['datetime'])
            
            return self.parsed_data
            
        except Exception as e:
            logger.error(f"❌ Error parsing CSV file {file_path}: {e}")
            raise
    
    def _parse_account_info(self, row: List[str]):
        """Parse account information section"""
        if len(row) >= 4:
            field_name = row[2]
            field_value = row[3]
            
            if field_name == 'Account':
                self.parsed_data['account_info']['account_number'] = field_value
            elif field_name == 'Name':
                self.parsed_data['account_info']['name'] = field_value
            elif field_name == 'Account Type':
                self.parsed_data['account_info']['account_type'] = field_value
    
    def _parse_trade(self, row: List[str]):
        """
        Parse trade data row
        Format: DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,Realized P/L,MTM P/L,Code
        """
        try:
            if len(row) < 15:
                return
            
            # Skip SubTotal rows
            if row[2] == '' and row[3] != '':  # SubTotal row pattern
                return
                
            data_discriminator = row[2]
            asset_category = row[3]
            currency = row[4]
            symbol = row[5]
            datetime_str = row[6]
            quantity = row[7]
            trade_price = row[8]
            close_price = row[9]
            proceeds = row[10]
            commission = row[11]
            basis = row[12]
            realized_pnl = row[13]
            mtm_pnl = row[14]
            code = row[15] if len(row) > 15 else ''
            
            # Skip empty or invalid rows
            if not symbol or not datetime_str or not quantity:
                return
            
            # Parse datetime
            try:
                # Format: "2024-09-19, 11:01:52"
                clean_datetime = datetime_str.strip('"')
                parsed_datetime = datetime.strptime(clean_datetime, '%Y-%m-%d, %H:%M:%S')
            except ValueError as e:
                logger.warning(f"Could not parse datetime '{datetime_str}': {e}")
                return
            
            # Convert numeric fields (handle comma-separated numbers)
            try:
                qty = float(quantity.replace(',', '')) if quantity else 0
                price = float(trade_price.replace(',', '')) if trade_price else 0
                proc = float(proceeds.replace(',', '')) if proceeds else 0
                comm = float(commission.replace(',', '')) if commission else 0
                
                # Determine action based on quantity
                action = 'BUY' if qty > 0 else 'SELL'
                
                trade_data = {
                    'id': f"csv_{symbol}_{clean_datetime.replace(' ', '_').replace(',', '').replace(':', '')}",
                    'order_id': f"csv_order_{parsed_datetime.strftime('%Y%m%d%H%M%S')}",
                    'account': self.parsed_data['account_info'].get('account_number', 'Unknown'),
                    'symbol': symbol,
                    'description': f"{symbol} {asset_category} - CSV Import",
                    'type': 'TRADE',
                    'action': action,
                    'quantity': abs(qty),
                    'price': price,
                    'amount': abs(proc),
                    'commission': abs(comm),
                    'currency': currency,
                    'exchange': 'IBKR',  # IBKR CSV data
                    'date': parsed_datetime.strftime('%Y-%m-%d'),
                    'time': parsed_datetime.strftime('%H:%M:%S'),
                    'datetime': parsed_datetime,
                    'settlement_date': (parsed_datetime + pd.Timedelta(days=2)).strftime('%Y-%m-%d'),
                    'source': 'ibkr_csv_import',
                    'contract_type': asset_category.upper(),
                    'execution_id': f"csv_exec_{parsed_datetime.strftime('%Y%m%d%H%M%S')}_{symbol}",
                    'net_amount': proc,
                    'realized_pnl': float(realized_pnl.replace(',', '')) if realized_pnl else 0,
                    'code': code,
                    'csv_data': {
                        'basis': float(basis.replace(',', '')) if basis else 0,
                        'mtm_pnl': float(mtm_pnl.replace(',', '')) if mtm_pnl else 0,
                        'data_discriminator': data_discriminator
                    }
                }
                
                self.parsed_data['trades'].append(trade_data)
                
            except ValueError as e:
                logger.warning(f"Could not parse numeric values for trade {symbol}: {e}")
                
        except Exception as e:
            logger.warning(f"Error parsing trade row: {e}")
    
    def _parse_dividend(self, row: List[str]):
        """Parse dividend data if present"""
        # Implementation for dividend parsing if needed
        pass
    
    def _parse_cash_transaction(self, row: List[str]):
        """Parse cash transactions if needed"""
        # Implementation for cash transaction parsing if needed
        pass
    
    def get_date_range(self) -> tuple:
        """Get the date range of parsed trades"""
        if not self.parsed_data['trades']:
            return None, None
            
        dates = [trade['datetime'] for trade in self.parsed_data['trades']]
        return min(dates), max(dates)
    
    def get_trade_summary(self) -> Dict[str, Any]:
        """Get summary statistics of parsed trades"""
        trades = self.parsed_data['trades']
        
        if not trades:
            return {}
        
        symbols = set(trade['symbol'] for trade in trades)
        total_volume = sum(trade['amount'] for trade in trades)
        total_commission = sum(trade['commission'] for trade in trades)
        
        buys = [t for t in trades if t['action'] == 'BUY']
        sells = [t for t in trades if t['action'] == 'SELL']
        
        date_range = self.get_date_range()
        
        return {
            'total_trades': len(trades),
            'unique_symbols': len(symbols),
            'symbols': sorted(list(symbols)),
            'total_volume': total_volume,
            'total_commission': total_commission,
            'buy_count': len(buys),
            'sell_count': len(sells),
            'date_range': {
                'start': date_range[0].isoformat() if date_range[0] else None,
                'end': date_range[1].isoformat() if date_range[1] else None
            },
            'account_number': self.parsed_data['account_info'].get('account_number', 'Unknown')
        }

def parse_multiple_csv_files(file_paths: List[str]) -> Dict[str, Any]:
    """
    Parse multiple CSV files and combine the results
    
    Args:
        file_paths: List of CSV file paths
        
    Returns:
        Combined parsed data from all files
    """
    combined_data = {
        'trades': [],
        'account_info': {},
        'dividends': [],
        'summary': {}
    }
    
    for file_path in file_paths:
        parser = IBKRCSVParser()
        file_data = parser.parse_csv_file(file_path)
        
        # Combine trades (with deduplication)
        existing_ids = set(trade['id'] for trade in combined_data['trades'])
        new_trades = [trade for trade in file_data['trades'] if trade['id'] not in existing_ids]
        combined_data['trades'].extend(new_trades)
        
        # Update account info
        combined_data['account_info'].update(file_data['account_info'])
        
        # Combine dividends
        combined_data['dividends'].extend(file_data['dividends'])
    
    # Sort all trades by date
    combined_data['trades'].sort(key=lambda x: x['datetime'])
    
    # Generate combined summary
    if combined_data['trades']:
        dates = [trade['datetime'] for trade in combined_data['trades']]
        symbols = set(trade['symbol'] for trade in combined_data['trades'])
        
        combined_data['summary'] = {
            'total_trades': len(combined_data['trades']),
            'unique_symbols': len(symbols),
            'symbols': sorted(list(symbols)),
            'date_range': {
                'start': min(dates).isoformat(),
                'end': max(dates).isoformat()
            },
            'files_processed': len(file_paths),
            'account_number': combined_data['account_info'].get('account_number', 'Unknown')
        }
    
    logger.info(f"🎯 Combined parsing complete: {len(combined_data['trades'])} total trades from {len(file_paths)} files")
    
    return combined_data 