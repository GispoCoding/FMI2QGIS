import enum

@enum.unique
class Settings(enum.Enum):
    fmi_download_url = 'https://opendata.fmi.fi/download'
