from typing import Dict, Any

from pydantic import BaseModel


class PydanticUtils:
    '''
    Utility class that holds static methods for doing things to pydantic models
    '''
    @staticmethod
    def flatten_model(model: BaseModel, prefix: str = "") -> Dict[str, Any]:
        '''
        Takes a pydantic model and maps all DATA to a its yaml path, with the key pattern being parent.parent2.key
        :param model: the pydantic object we want to flatten
        :param prefix: prefix to append to the start of a key for when we recursivly navigate the model tree
        :return: dictionary of each key path in the model yaml -> Object it holds
        '''
        flattened = {}
        for field_name, value in model.model_dump().items():
            full_key = f"{prefix}{field_name}"

            if isinstance(value, BaseModel):
                # Recursively flatten nested models
                flattened.update(PydanticUtils.flatten_model(value, prefix=f"{full_key}_"))
            else:
                flattened[full_key] = value
        return flattened