"""
Mapping service for converting non-standard metric names to standard metric names using LLM.
"""

from typing import Dict, List, Tuple, Optional
import difflib
import logging
import json
import threading
from pathlib import Path
from .exceptions import MappingError
from ..llm.llm_client import LLMClient


class MappingService:
    """Service for mapping non-standard metric names to standard metric names."""

    def __init__(self, metric_definitions: Dict, similarity_threshold: float = 0.85):
        """
        Initialize the mapping service.

        Args:
            metric_definitions: Dictionary of standard metric definitions
            similarity_threshold: Minimum similarity score to consider a match
        """
        self.metric_definitions = metric_definitions
        self.similarity_threshold = similarity_threshold
        self.standard_metrics = set(metric_definitions.keys())
        self.logger = logging.getLogger(__name__)
        self.llm_client = LLMClient()
        self.dynamic_mappings_path = Path("dynamic_mappings.json")
        self._load_dynamic_mappings()
        self._lock = threading.Lock()

    def map_metric_name(self, input_name: str) -> Tuple[str, float]:
        """
        Map a single non-standard metric name to the closest standard metric name.

        Args:
            input_name: Non-standard metric name to map

        Returns:
            Tuple of (mapped_name, confidence_score)

        Raises:
            MappingError: If no suitable mapping is found
        """
        input_name = self._normalize_metric_name(input_name)

        # Check dynamic mappings first
        if input_name in self.dynamic_mappings:
            return self.dynamic_mappings[input_name], 1.0

        # Direct match check
        if input_name in self.standard_metrics:
            return input_name, 1.0

        # Find closest matches using similarity scoring
        matches = []
        for standard_name in self.standard_metrics:
            score = self._calculate_similarity(input_name, standard_name)
            if score >= self.similarity_threshold:
                matches.append((standard_name, score))

        if matches:
            # Sort by similarity score
            matches.sort(key=lambda x: x[1], reverse=True)

            # Check for ambiguous matches
            if len(matches) > 1 and self._is_ambiguous(matches):
                self.logger.warning(
                    f"Ambiguous mapping for {input_name}: {matches[:3]}"
                )

            return matches[0]

        # If no matches found, try LLM-based mapping
        try:
            context = {"mapped_metrics": self.dynamic_mappings}
            mapped_name, confidence = self._map_with_llm(input_name, context)
            return mapped_name, confidence
        except Exception as e:
            self.logger.error(f"LLM mapping failed for {input_name}: {str(e)}")
            raise MappingError(f"No suitable mapping found for metric: {input_name}")

    def map_metric_names(self, input_names: List[str]) -> Dict[str, Tuple[str, float]]:
        """
        Map multiple non-standard metric names to standard names.

        Args:
            input_names: List of non-standard metric names

        Returns:
            Dictionary mapping input names to (standard_name, confidence_score) tuples
        """
        mappings = {}
        unmapped = []

        for name in input_names:
            try:
                mapped_name, score = self.map_metric_name(name)
                mappings[name] = (mapped_name, score)
            except MappingError as e:
                unmapped.append(name)
                self.logger.error(f"Failed to map metric: {e}")

        if unmapped:
            self.logger.warning(f"Failed to map metrics: {unmapped}")

        return mappings

    def validate_mapping(self, input_name: str, mapped_name: str) -> bool:
        """
        Validate if a mapping is acceptable based on metric definitions.

        Args:
            input_name: Original input name
            mapped_name: Proposed standard metric name

        Returns:
            Boolean indicating if mapping is valid
        """
        if mapped_name not in self.metric_definitions:
            return False

        # Additional validation could be added here based on metric properties
        return True

    def _normalize_metric_name(self, name: str) -> str:
        """Normalize metric name for comparison."""
        return name.lower().replace(" ", "_").strip()

    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity score between two metric names."""
        return difflib.SequenceMatcher(None, name1, name2).ratio()

    def _is_ambiguous(
        self, matches: List[Tuple[str, float]], threshold: float = 0.05
    ) -> bool:
        """
        Check if matches are ambiguous based on score differences.

        Args:
            matches: List of (name, score) tuples
            threshold: Maximum score difference to consider ambiguous

        Returns:
            Boolean indicating if matches are ambiguous
        """
        if len(matches) < 2:
            return False

        return (matches[0][1] - matches[1][1]) < threshold

    def get_metric_info(self, metric_name: str) -> Optional[Dict]:
        """
        Get detailed information about a standard metric.

        Args:
            metric_name: Standard metric name

        Returns:
            Dictionary containing metric information or None if not found
        """
        return self.metric_definitions.get(metric_name)

    def _map_with_llm(self, input_name: str, context: Dict) -> Tuple[str, float]:
        """
        Use LLM to map an unknown metric name to a standard metric.

        Args:
            input_name: Non-standard metric name to map
            context: Dictionary containing mapping context

        Returns:
            Tuple of (mapped_name, confidence_score)

        Raises:
            MappingError: If LLM mapping fails or produces invalid result
        """
        prompt = self._generate_mapping_prompt(input_name, context)

        try:
            llm_response = self.llm_client.generate_mapping(prompt)
            mapped_name = self._normalize_metric_name(llm_response["mapped_name"])
            confidence = float(llm_response["confidence"])

            if not self.validate_mapping(input_name, mapped_name):
                raise MappingError(f"LLM suggested invalid mapping: {mapped_name}")

            # Store the new mapping
            with self._lock:
                self.dynamic_mappings[input_name] = mapped_name
                self._save_dynamic_mappings()

            return mapped_name, confidence

        except Exception as e:
            raise MappingError(f"LLM mapping failed: {str(e)}")

    def _generate_mapping_prompt(self, input_name: str, context: Dict) -> str:
        """Generate context-aware prompt for LLM mapping."""
        prompt = f"""Map the financial metric name '{input_name}' to one of the following standard metrics:
        {", ".join(sorted(self.standard_metrics))}
        
        Previously mapped examples:
        {json.dumps(context["mapped_metrics"], indent=2)}
        
        Return a JSON object with:
        - mapped_name: The standard metric name
        - confidence: A float between 0 and 1
        """
        return prompt

    def _load_dynamic_mappings(self):
        """Load dynamic mappings from file."""
        self.dynamic_mappings = {}
        if self.dynamic_mappings_path.exists():
            try:
                with open(self.dynamic_mappings_path, "r") as f:
                    self.dynamic_mappings = json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load dynamic mappings: {str(e)}")

    def _save_dynamic_mappings(self):
        """Save dynamic mappings to file."""
        try:
            with open(self.dynamic_mappings_path, "w") as f:
                json.dump(self.dynamic_mappings, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save dynamic mappings: {str(e)}")
