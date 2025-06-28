"""
Trainer module for forecasting models.
"""

import os
import pandas as pd
import numpy as np
import json
import logging
import argparse
from typing import Dict, List, Tuple, Any, Optional, Union
from sklearn.model_selection import cross_val_score, KFold
from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor, 
    AdaBoostRegressor,
    ExtraTreesRegressor
)
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score

from ..config.constants import (
    DEFAULT_OUTPUT_DIR, DEFAULT_DATA_DIR, DEFAULT_RANDOM_STATE, 
    DEFAULT_CV_FOLDS, COMBINED_DATA_PATTERN, PREDICTIONS_PATTERN
)
from ..utils.file_utils import find_latest_file, get_next_friday, clean_old_files

# Configure module logger
logger = logging.getLogger(__name__)

class ModelTrainer:
    """
    Trains regression models and predicts next Friday's values.
    """
    
    def __init__(self, 
                 data_dir: str = DEFAULT_DATA_DIR,
                 output_dir: str = DEFAULT_OUTPUT_DIR,
                 random_state: int = DEFAULT_RANDOM_STATE,
                 n_cv_folds: int = DEFAULT_CV_FOLDS):
        """
        Initialize the ModelTrainer.
        
        Args:
            data_dir: Directory containing input data files
            output_dir: Directory to save prediction outputs
            random_state: Random seed for reproducibility
            n_cv_folds: Number of cross-validation folds
        """
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.random_state = random_state
        self.n_cv_folds = n_cv_folds
        self.best_model = None
        self.best_model_name = None
        self.encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
        self.scaler = StandardScaler()
        
    def _initialize_models(self) -> Dict[str, Any]:
        """
        Initialize regression models to evaluate.
        
        Returns:
            Dictionary mapping model names to model objects
        """
        return {
            "Random Forest": RandomForestRegressor(random_state=self.random_state),
            "Gradient Boosting": GradientBoostingRegressor(random_state=self.random_state),
            "AdaBoost": AdaBoostRegressor(random_state=self.random_state),
            "Linear Regression": LinearRegression(),
            "Ridge Regression": Ridge(),
            "Lasso Regression": Lasso(),
            "Support Vector Regression": SVR(),
            "Decision Tree": DecisionTreeRegressor(random_state=self.random_state),
            "K-Neighbors": KNeighborsRegressor(),
            "Extra Trees": ExtraTreesRegressor(random_state=self.random_state)
        }
    
    def _load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load and prepare the dataset.
        
        Returns:
            Tuple containing the training data and test data
        
        Raises:
            FileNotFoundError: If no combined data file is found
        """
        try:
            # Find the latest combined_data file from the data_dir (should be input directory)
            data_file = find_latest_file(self.data_dir, COMBINED_DATA_PATTERN)
            df = pd.read_csv(data_file)
            logger.info(f"Loaded data from {data_file}, shape: {df.shape}")
            
            # Forward fill specific columns if they have NaN values
            columns_to_ffill = ['CPI', 'UnemploymentRate', 'FEDFUNDS', 'DFF', 'GDP']
            existing_columns = [col for col in columns_to_ffill if col in df.columns]
            
            if existing_columns:
                # Check if any of the columns have NaN values
                has_nan = df[existing_columns].isna().any().any()
                if has_nan:
                    logger.info(f"Forward filling NaN values in columns: {existing_columns}")
                    df[existing_columns] = df[existing_columns].fillna(method='ffill')
                    logger.info(f"Forward fill completed for {existing_columns}")
                else:
                    logger.info(f"No NaN values found in {existing_columns}")
            else:
                logger.info("None of the specified ffill columns found in data")
            
            # Split into training and test data
            test = df[df["actual"].isna()]
            train = df.dropna()
            
            # Drop Date column as it's not needed for modeling
            if "Date" in train.columns:
                train = train.drop(columns=["Date"])
            if "Date" in test.columns:
                test = test.drop(columns=["Date"])
                
            return train, test
            
        except FileNotFoundError as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def _preprocess_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str], List[str]]:
        """
        Preprocess the data for model training.
        
        Args:
            df: DataFrame to preprocess
            
        Returns:
            Tuple containing:
                - Processed feature matrix
                - Target vector
                - List of categorical column names
                - List of numerical column names
        """
        # Separate features and target
        X = df.drop("actual", axis=1)
        y = df[["actual"]].values.ravel()
        
        # Identify categorical and numerical columns
        categorical_cols = X.select_dtypes(include=['object']).columns.tolist()
        numerical_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        
        # Process features
        if categorical_cols:
            self.encoder.fit(X[categorical_cols])
            X_encoded = self.encoder.transform(X[categorical_cols])
            
            # Scale numerical features
            self.scaler.fit(X[numerical_cols])
            X_num = self.scaler.transform(X[numerical_cols])
            
            # Combine numerical and categorical features
            X_processed = np.hstack([X_num, X_encoded])
        else:
            self.scaler.fit(X)
            X_processed = self.scaler.transform(X)
        
        return X_processed, y, categorical_cols, numerical_cols
    
    def _evaluate_models(self, X: np.ndarray, y: np.ndarray) -> pd.DataFrame:
        """
        Evaluate multiple regression models using cross-validation.
        
        Args:
            X: Feature matrix
            y: Target vector
            
        Returns:
            DataFrame with model evaluation metrics
        """
        models = self._initialize_models()
        cv = KFold(n_splits=self.n_cv_folds, shuffle=True, random_state=self.random_state)
        
        results = []
        for name, model in models.items():
            logger.info(f"Evaluating {name}...")
            
            # Calculate cross-validation scores
            scores_mae = cross_val_score(
                model, X, y, cv=cv, scoring='neg_mean_absolute_error'
            )
            scores_r2 = cross_val_score(
                model, X, y, cv=cv, scoring='r2'
            )
            
            # Record results
            results.append({
                'model': name,
                'mean_mae': -scores_mae.mean(),
                'std_mae': scores_mae.std(),
                'mean_r2': scores_r2.mean(),
                'std_r2': scores_r2.std()
            })
            
            logger.debug(
                f"{name} - Mean MAE: {-scores_mae.mean():.4f} "
                f"(±{scores_mae.std():.4f}), Mean R²: {scores_r2.mean():.4f} "
                f"(±{scores_r2.std():.4f})"
            )
        
        return pd.DataFrame(results)
    
    def _select_best_model(self, results_df: pd.DataFrame) -> Tuple[str, Any]:
        """
        Select the best model based on mean MAE.
        
        Args:
            results_df: DataFrame with model evaluation results
            
        Returns:
            Tuple with best model name and model object
        """
        # Select model with lowest mean MAE
        best_model_name = results_df.sort_values('mean_mae').iloc[0]['model']
        
        # Get the model object
        models = self._initialize_models()
        best_model = models[best_model_name]
        
        logger.info(f"Best model: {best_model_name}")
        return best_model_name, best_model
    
    def _preprocess_test_data(self, 
                             test_df: pd.DataFrame, 
                             categorical_cols: List[str],
                             numerical_cols: List[str]) -> np.ndarray:
        """
        Preprocess test data using fitted encoder and scaler.
        
        Args:
            test_df: Test DataFrame
            categorical_cols: List of categorical column names
            numerical_cols: List of numerical column names
            
        Returns:
            Processed test feature matrix
        """
        if categorical_cols:
            test_encoded = self.encoder.transform(test_df[categorical_cols])
            test_num = self.scaler.transform(test_df[numerical_cols])
            return np.hstack([test_num, test_encoded])
        else:
            return self.scaler.transform(test_df)
    
    def _save_predictions(self, test_df: pd.DataFrame) -> str:
        """
        Save predictions as ticker:prediction pairs in JSON format.
        
        Args:
            test_df: DataFrame with predictions
            
        Returns:
            Path to saved prediction file
        """
        # Clean up old prediction files
        clean_old_files(self.output_dir, PREDICTIONS_PATTERN)
        
        # Get next Friday date
        next_friday = get_next_friday()
        
        # Create predictions dictionary with date at the beginning
        pred_dict = {
            "prediction_date": next_friday,
            "predictions": dict(zip(test_df['ticker'], test_df['prediction']))
        }
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Save predictions to JSON with simplified filename
        json_path = os.path.join(self.output_dir, "next_friday_predictions.json")
        
        with open(json_path, 'w') as f:
            json.dump(pred_dict, f, indent=2)
            
        logger.info(f"Predictions saved to {json_path}")
        return json_path
    
    def train_and_predict(self) -> Tuple[str, Dict[str, float]]:
        """
        Train models, select the best one, and make predictions.
        
        Returns:
            Tuple containing:
                - Path to saved predictions file
                - Dictionary of ticker:prediction pairs
        """
        logger.info("Starting model training and prediction process...")
        
        # Load and prepare data
        train_df, test_df = self._load_data()
        
        # Preprocess training data
        X_train, y_train, categorical_cols, numerical_cols = self._preprocess_data(train_df)
        
        # Evaluate models and select the best
        results_df = self._evaluate_models(X_train, y_train)
        self.best_model_name, self.best_model = self._select_best_model(results_df)
        
        # Train the best model on all data
        self.best_model.fit(X_train, y_train)
        logger.info(f"Model training complete using {self.best_model_name} model.")
        
        # Preprocess test data
        X_test = self._preprocess_test_data(test_df, categorical_cols, numerical_cols)
        
        # Generate predictions
        test_df['prediction'] = self.best_model.predict(X_test)
        
        # Save predictions
        json_path = self._save_predictions(test_df)
        
        # Return results
        return json_path, dict(zip(test_df['ticker'], test_df['prediction']))


def configure_logging(level: str = 'INFO') -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Train regression models and predict next Friday's values."
    )
    parser.add_argument(
        '--log-level', 
        dest='loglevel', 
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level (default: INFO)'
    )
    parser.add_argument(
        '--data-dir',
        dest='data_dir',
        default='forecasting/data/output',
        help='Directory containing input data files'
    )
    parser.add_argument(
        '--output-dir',
        dest='output_dir',
        default='forecasting/data/output',
        help='Directory to save prediction outputs'
    )
    return parser.parse_args()

def main() -> None:
    """
    Main entry point for the application.
    """
    # Parse command-line arguments
    args = parse_args()
    
    # Configure logging
    configure_logging(args.loglevel)
    
    # Create and use the model trainer
    trainer = ModelTrainer(
        data_dir=args.data_dir,
        output_dir=args.output_dir
    )
    
    # Train and generate predictions
    json_path, predictions = trainer.train_and_predict()
    
    logger.info(f"Process complete.")

if __name__ == "__main__":
    main()
