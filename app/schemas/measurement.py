from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class MeasurementItem(BaseModel):
    feature_id: int
    geometry_type: str
    measurement_type: Optional[str] = None
    measurement_value: Optional[float] = None
    measurement_unit: Optional[str] = None
    processing_status: str = "SUCCESS"
    error_message: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class FileMeasurementsResponse(BaseModel):
    file_id: str
    measurements: List[MeasurementItem]

    model_config = ConfigDict(from_attributes=True)
