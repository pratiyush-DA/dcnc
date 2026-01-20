"""
Clustering Hyperparameters Configuration
Fine-tuned values for production-grade anomaly detection
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class NumericClusteringConfig:
    """Configuration for numeric clustering."""
    
    # Isolation Forest parameters
    contamination: str = "auto"  # "auto" or float (0.01-0.5)
    n_estimators: int = 100      # Number of trees
    
    # IQR parameters
    iqr_factor: float = 1.5      # Standard is 1.5, use 2.0 for lenient
    
    # Z-score parameters
    z_threshold: float = 3.0     # Standard is 3.0 (99.7% confidence)
    
    # Semantic constraints for known subtypes
    semantic_bounds: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "age": {"min": 0, "max": 120, "type": "integer"},
        "rating": {"min": 0, "max": 10},
        "year": {"min": 1900, "max": 2100, "type": "integer"},
        "latitude": {"min": -90, "max": 90},
        "longitude": {"min": -180, "max": 180},
        "percentage": {"min": 0, "max": 100},
        "temperature": {"min": -273.15, "max": 1000},
    })


@dataclass
class StringClusteringConfig:
    """Configuration for string clustering."""
    
    # DBSCAN parameters
    eps: float = 0.5             # Neighborhood radius (0.3-0.8 for strings)
    min_samples: int = 3         # Minimum cluster size
    min_cluster_ratio: float = 0.1  # Minimum % for valid cluster
    
    # Feature extraction weights (for tuning)
    length_weight: float = 1.0
    word_count_weight: float = 1.0
    alpha_ratio_weight: float = 1.0
    pattern_weight: float = 1.0


@dataclass
class DateTimeClusteringConfig:
    """Configuration for datetime clustering."""
    
    # Year range validation
    min_year: int = 1900
    max_year: int = 2100
    
    # Unix timestamp range
    min_timestamp: int = 0              # 1970-01-01
    max_timestamp: int = 4102444800     # 2100-01-01


@dataclass
class IdentifierClusteringConfig:
    """Configuration for identifier clustering."""
    
    # Pattern matching
    pattern_threshold: float = 0.1     # Minimum % for valid pattern
    majority_threshold: float = 0.6    # Threshold for single-pattern dominance
    
    # Entropy analysis
    entropy_factor: float = 0.3        # Anomaly if entropy < avg * factor
    
    # Uniqueness
    min_uniqueness: float = 0.5        # Minimum unique ratio for identifiers


@dataclass
class ClusteringConfig:
    """Master clustering configuration."""
    
    numeric: NumericClusteringConfig = field(default_factory=NumericClusteringConfig)
    string: StringClusteringConfig = field(default_factory=StringClusteringConfig)
    datetime: DateTimeClusteringConfig = field(default_factory=DateTimeClusteringConfig)
    identifier: IdentifierClusteringConfig = field(default_factory=IdentifierClusteringConfig)
    
    @classmethod
    def get_default(cls) -> "ClusteringConfig":
        """Get default production configuration."""
        return cls()
    
    @classmethod
    def get_lenient(cls) -> "ClusteringConfig":
        """Get lenient configuration (fewer false positives)."""
        return cls(
            numeric=NumericClusteringConfig(
                iqr_factor=2.0,      # More lenient IQR
                z_threshold=3.5,     # More lenient z-score
            ),
            string=StringClusteringConfig(
                eps=0.6,             # Larger clusters
                min_samples=2,       # Smaller minimum
            ),
        )
    
    @classmethod
    def get_strict(cls) -> "ClusteringConfig":
        """Get strict configuration (fewer false negatives)."""
        return cls(
            numeric=NumericClusteringConfig(
                iqr_factor=1.0,      # Stricter IQR
                z_threshold=2.5,     # Stricter z-score
            ),
            string=StringClusteringConfig(
                eps=0.4,             # Tighter clusters
                min_samples=5,       # Larger minimum
            ),
        )


# Global default config
DEFAULT_CONFIG = ClusteringConfig.get_default()


def get_config(preset: str = "default") -> ClusteringConfig:
    """
    Get clustering configuration by preset name.
    
    Args:
        preset: One of "default", "lenient", "strict"
    """
    if preset == "lenient":
        return ClusteringConfig.get_lenient()
    elif preset == "strict":
        return ClusteringConfig.get_strict()
    return ClusteringConfig.get_default()
