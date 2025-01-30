import json

import numpy as np
from numpy import dot
from numpy.linalg import norm
from local_config import LocalLogging

logger = LocalLogging.get_local_logger("Math_Utils")
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
        answer = dot(vec1, vec2) / (norm(vec1) * norm(vec2))
        return dot(vec1, vec2) / (norm(vec1) * norm(vec2))

    @staticmethod
    def match_embedded_vector_batches(element_vector_list: np.ndarray, match_vector_list: np.ndarray):
        '''
        Utility method that allows you to take two list of vectors where each vector are the same size (likely going to be embedded vectors)
        and then finds which vector from the match_vector_list is the closest match for each search vector

        :param element_vector_list: list(embedded_vectors) that represent N elements vector embedding
        :param match_vector_list: list(embedded_vectors) that represent M strings that we want to try and match to each element
        :return: list of integers where the corresponding index of each integer tells us what element it is mapping,
                    and the value at the index corresponds to index of match_vector_list that most matches it
        '''
        if element_vector_list.ndim != 2 or match_vector_list.ndim != 2:
            logger.error("Given vectors for match_embedded_vector_batches must both be 2 dimensional numpy arrays, "
                         "each row correlating to an embedded vector")
        if element_vector_list.shape[1] != match_vector_list.shape[0]:
            logger.error("Given vectors for match_embedded_vector_batches must be able to be multiplied.\n"
                         + f"element_vector_list size - {element_vector_list.shape[0]} x {element_vector_list.shape[1]}"
                         + f"element_vector_list size - {match_vector_list.shape[0]} x {match_vector_list.shape[1]}")

        # We do not need to normalize every vector because each embedding vector should already be normalized
        similarity_matrix = np.dot(element_vector_list, match_vector_list.T)  # Direct cosine scores
        best_match_indices = np.argmax(similarity_matrix, axis=1)
        return best_match_indices

class RunningAverage:
    def __init__(self):
        self.count = 0
        self.total = 0
        self.average = 0.0

    def update(self, num):
        self.count += 1
        self.total += num
        self.average = self.total / self.count

    def average(self):
        return self.average()

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)