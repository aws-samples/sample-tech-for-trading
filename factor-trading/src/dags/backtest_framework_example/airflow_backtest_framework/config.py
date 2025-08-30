"""
Configuration module for the Airflow Backtest Framework.
"""

import datetime
from typing import Dict, List, Optional, Any, Union
from itertools import product


class BacktestConfig:
    """
    Configuration for a backtest or set of backtests.
    """
    
    def __init__(self, 
                 strategy_class: str,
                 start_date: Union[str, datetime.date],
                 end_date: Union[str, datetime.date],
                 initial_capital: float = 1000000.0,
                 param_grid: Optional[Dict[str, List[Any]]] = None,
                 factors: Optional[List[str]] = None,
                 universe: Optional[List[str]] = None,
                 rebalance_period: Optional[int] = None,
                 take_profit_pct: Optional[float] = None,
                 stop_loss_pct: Optional[float] = None,
                 cooldown_period: Optional[int] = None,
                 batch_job_queue: Optional[str] = None,
                 batch_job_definition: Optional[str] = None,
                 s3_bucket: Optional[str] = None,
                 db_config: Optional[Dict[str, Any]] = None):
        """
        Initialize backtest configuration.
        
        Args:
            strategy_class: Strategy class name
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Initial capital amount
            param_grid: Parameter combinations grid
            factors: List of factors
            universe: List of securities
            rebalance_period: Days between rebalances
            take_profit_pct: Take profit percentage
            stop_loss_pct: Stop loss percentage
            cooldown_period: Cooldown period in days
            batch_job_queue: AWS Batch job queue
            batch_job_definition: AWS Batch job definition
            s3_bucket: S3 results bucket
            db_config: Database configuration
        """
        self.strategy_class = strategy_class
        
        # Convert dates to string format if they are datetime objects
        if isinstance(start_date, datetime.date):
            self.start_date = start_date.strftime('%Y-%m-%d')
        else:
            self.start_date = start_date
            
        if isinstance(end_date, datetime.date):
            self.end_date = end_date.strftime('%Y-%m-%d')
        else:
            self.end_date = end_date
            
        self.initial_capital = initial_capital
        self.param_grid = param_grid or {}
        self.factors = factors or []
        self.universe = universe or []
        self.rebalance_period = rebalance_period
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.cooldown_period = cooldown_period
        self.batch_job_queue = batch_job_queue
        self.batch_job_definition = batch_job_definition
        self.s3_bucket = s3_bucket
        self.db_config = db_config or {}
        
    def validate(self) -> bool:
        """
        Validate the configuration.
        
        Returns:
            bool: True if the configuration is valid, False otherwise
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check required fields
        if not self.strategy_class:
            raise ValueError("Strategy class is required")
        
        if not self.start_date:
            raise ValueError("Start date is required")
            
        if not self.end_date:
            raise ValueError("End date is required")
            
        # Validate dates
        try:
            start = datetime.datetime.strptime(self.start_date, '%Y-%m-%d').date()
            end = datetime.datetime.strptime(self.end_date, '%Y-%m-%d').date()
            
            if start >= end:
                raise ValueError("Start date must be before end date")
        except ValueError as e:
            if "does not match format" in str(e):
                raise ValueError("Dates must be in YYYY-MM-DD format")
            else:
                raise
                
        # Validate numeric values
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
            
        if self.rebalance_period is not None and self.rebalance_period <= 0:
            raise ValueError("Rebalance period must be positive")
            
        if self.take_profit_pct is not None and self.take_profit_pct <= 0:
            raise ValueError("Take profit percentage must be positive")
            
        if self.stop_loss_pct is not None and self.stop_loss_pct <= 0:
            raise ValueError("Stop loss percentage must be positive")
            
        if self.cooldown_period is not None and self.cooldown_period < 0:
            raise ValueError("Cooldown period must be non-negative")
            
        return True
        
    def generate_combinations(self) -> List[Dict[str, Any]]:
        """
        Generate parameter combinations based on param_grid.
        
        Returns:
            List[Dict[str, Any]]: List of parameter combinations
        """
        if not self.param_grid:
            # If no param_grid is provided, return a single configuration
            return [self.to_dict()]
            
        # Extract keys and values from param_grid
        keys = list(self.param_grid.keys())
        values = list(self.param_grid.values())
        
        # Generate all combinations
        combinations = []
        for combo_values in product(*values):
            combo = {keys[i]: combo_values[i] for i in range(len(keys))}
            
            # Create a new configuration with this combination
            config = self.to_dict()
            
            # Update with the combination values
            for key, value in combo.items():
                if key == 'strategy_params':
                    # Special handling for strategy_params
                    config['strategy_params'] = value
                else:
                    config[key] = value
                    
            combinations.append(config)
            
        return combinations
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the configuration
        """
        config = {
            'strategy_class': self.strategy_class,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_capital': self.initial_capital,
            'factors': self.factors,
            'universe': self.universe,
        }
        
        # Add optional parameters if they are set
        if self.rebalance_period is not None:
            config['rebalance_period'] = self.rebalance_period
            
        if self.take_profit_pct is not None:
            config['take_profit_pct'] = self.take_profit_pct
            
        if self.stop_loss_pct is not None:
            config['stop_loss_pct'] = self.stop_loss_pct
            
        if self.cooldown_period is not None:
            config['cooldown_period'] = self.cooldown_period
            
        # Add strategy_params if they are in param_grid
        if 'strategy_params' in self.param_grid:
            # Use the first set of strategy_params as default
            config['strategy_params'] = self.param_grid['strategy_params'][0]
            
        # Add database configuration if provided
        if self.db_config:
            config['db_config'] = self.db_config
            
        # Add S3 bucket if provided
        if self.s3_bucket:
            config['s3_bucket'] = self.s3_bucket
            
        return config


def create_batch_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a configuration for AWS Batch job.
        
        Args:
            config: Backtest configuration
            
        Returns:
            Dict[str, Any]: AWS Batch job configuration for container_overrides
        """
        # Convert config to environment variables
        env_vars = []
        
        # Add basic configuration
        env_vars.append({'name': 'STRATEGY_CLASS', 'value': config['strategy_class']})
        env_vars.append({'name': 'START_DATE', 'value': config['start_date']})
        env_vars.append({'name': 'END_DATE', 'value': config['end_date']})
        env_vars.append({'name': 'INITIAL_CAPITAL', 'value': str(config['initial_capital'])})
        
        # Add factors if provided
        if config.get('factors'):
            env_vars.append({'name': 'FACTORS', 'value': ','.join(config['factors'])})
        
        # Add universe if provided
        if config.get('universe'):
            env_vars.append({'name': 'UNIVERSE', 'value': ','.join(config['universe'])})
        
        # Add optional parameters
        if 'rebalance_period' in config:
            env_vars.append({'name': 'REBALANCE_PERIOD', 'value': str(config['rebalance_period'])})
            
        # Note: The batch job expects take_profit and stop_loss (without _pct)
        if 'take_profit_pct' in config:
            env_vars.append({'name': 'TAKE_PROFIT', 'value': str(config['take_profit_pct'])})
            
        if 'stop_loss_pct' in config:
            env_vars.append({'name': 'STOP_LOSS', 'value': str(config['stop_loss_pct'])})
            
        if 'cooldown_period' in config:
            env_vars.append({'name': 'COOLDOWN_PERIOD', 'value': str(config['cooldown_period'])})
        
        # Add strategy parameters if provided
        if 'strategy_params' in config:
            # Extract and add individual strategy parameters as separate environment variables
            for key, value in config['strategy_params'].items():
                env_vars.append({'name': key.upper(), 'value': str(value)})
        
        # Add database configuration if provided
        if 'db_config' in config:
            # Map db_config keys to generic database environment variable names
            db_env_var_mapping = {
                'db_host': 'DB_HOST',
                'db_port': 'DB_PORT',
                'db_user': 'DB_USER',
                'db_password': 'DB_PASSWORD',
                'db_database': 'DB_DATABASE'
            }
            
            for key, value in config['db_config'].items():
                db_env_var = db_env_var_mapping.get(key)
                if db_env_var:
                    env_vars.append({'name': db_env_var, 'value': str(value)})
        
        # Add results bucket if provided
        if 's3_bucket' in config:
            env_vars.append({'name': 'RESULTS_BUCKET', 'value': config['s3_bucket']})
        
        # Create batch job configuration in the format expected by container_overrides
        batch_config = {
            'environment': env_vars
        }
        
        return batch_config