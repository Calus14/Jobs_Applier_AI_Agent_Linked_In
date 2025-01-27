import logging

from numpy import dot
from numpy.linalg import norm

logger = logging.getLogger("Math_Utils")
class MathUtils:
    @staticmethod
    def cosine_similarity(vec1, vec2):
        if (not vec1 or not vec2):
            logger.error("Passed a null vector when trying to compute the cosine_similarity!")
            return 0.0
        if (len(vec1) == 0 or len(vec2) == 0):
            logger.error("Passed an empty vector when trying to compute the cosine_similarity!")
            return 0.0
        if len(vec1) != len(vec2):
            logger.error(f"Passed two vectors of different length to compute the cosine_similarity! Length of vector 1:{len(vec1)} Length of vector 2:{len(vec2)}")
            return 0.0
        return dot(vec1, vec2) / (norm(vec1) * norm(vec2))