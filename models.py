from pydantic import BaseModel, Field, AliasChoices, AliasPath, ConfigDict, field_validator


class GeoPoint(BaseModel):
    lon: float
    lat: float


class Access(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(validation_alias=AliasChoices("accid", "id"))
    name: str = Field(validation_alias=AliasChoices("accname", "name"))
    short_name: int | None = Field(validation_alias=AliasChoices("accshortname", "short_name"))
    x_lambert_93: int = Field(validation_alias=AliasChoices("accxespg2154", "x_lambert_93"))
    y_lambert_93: int = Field(validation_alias=AliasChoices("accyespg2154", "y_lambert_93"))
    geo_point: GeoPoint = Field(validation_alias=AliasChoices("accgeopoint", "geo_point"))


class Line(BaseModel):
    id: str
    name: str
    icon_url: str | None


class Zone(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(validation_alias=AliasChoices("zdaid", "id"))
    name: str = Field(validation_alias=AliasChoices("zdaname", "name"))
    type: str | None = Field(validation_alias=AliasChoices("zdatype", "type"))
    town: str = Field(validation_alias=AliasChoices("zdatown", "town"))
    postal_region: str = Field(validation_alias=AliasChoices("zdapostalregion", "postal_region"))
    x_lambert_93: int = Field(validation_alias=AliasChoices("zdaxepsg2154", "x_lambert_93"))
    y_lambert_93: int = Field(validation_alias=AliasChoices("zdayepsg2154", "y_lambert_93"))
    accesses: list[Access] = []
    lines: list[Line] = []


class ZoneAccessRelationship(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    zone_id: str = Field(validation_alias=AliasChoices("zdaid", "zone_id"))
    access_id: str = Field(validation_alias=AliasChoices("accid", "access_id"))


class ZoneLineRelationship(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    zone_id: str = Field(validation_alias=AliasChoices("id_ref_zda", "zone_id"))
    line_id: str = Field(validation_alias=AliasChoices("idrefliga", "line_id"))
    line_name: str = Field(validation_alias=AliasChoices("res_com", "line_name"))
    line_icon_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(AliasPath("picto", "url"), "line_icon_url"),
    )
    mode: str

    @field_validator("zone_id", mode="before")
    @classmethod
    def _zone_id_to_str(cls, v):
        return None if v is None else str(v)
