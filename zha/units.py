"""Units of measure for Zigbee Home Automation."""

from enum import Enum, StrEnum
from typing import Final

_UNITS_OF_MEASURE = {}


def register_unit[T: type[StrEnum]](enum: T) -> T:
    """Register a unit of measure."""

    assert enum.__name__ not in _UNITS_OF_MEASURE
    _UNITS_OF_MEASURE[enum.__name__] = enum

    return enum


def validate_unit(external_unit: Enum) -> Enum:
    """Validate and return a unit of measure."""
    return _UNITS_OF_MEASURE[type(external_unit).__name__](external_unit.value)


# Percentage units
PERCENTAGE: Final[str] = "%"

# UV Index units
UV_INDEX: Final = "UV index"


@register_unit
class UnitOfTemperature(StrEnum):
    """Temperature units."""

    CELSIUS = "°C"
    FAHRENHEIT = "°F"
    KELVIN = "K"


@register_unit
class UnitOfArea(StrEnum):
    """Area units."""

    SQUARE_METERS = "m²"


@register_unit
class UnitOfConductivity(StrEnum):
    """Conductivity units."""

    SIEMENS_PER_CM = "S/cm"
    MICROSIEMENS_PER_CM = "µS/cm"
    MILLISIEMENS_PER_CM = "mS/cm"


@register_unit
class UnitOfMass(StrEnum):
    """Mass units."""

    GRAMS = "g"
    KILOGRAMS = "kg"
    MILLIGRAMS = "mg"
    MICROGRAMS = "µg"
    OUNCES = "oz"
    POUNDS = "lb"
    STONES = "st"


@register_unit
class UnitOfPressure(StrEnum):
    """Pressure units."""

    PA = "Pa"
    HPA = "hPa"
    KPA = "kPa"
    BAR = "bar"
    CBAR = "cbar"
    MBAR = "mbar"
    MMHG = "mmHg"
    INHG = "inHg"
    PSI = "psi"


@register_unit
class UnitOfSoundPressure(StrEnum):
    """Sound pressure units."""

    DECIBEL = "dB"
    WEIGHTED_DECIBEL_A = "dBA"


@register_unit
class UnitOfPower(StrEnum):
    """Power units."""

    WATT = "W"
    KILO_WATT = "kW"
    BTU_PER_HOUR = "BTU/h"


@register_unit
class UnitOfApparentPower(StrEnum):
    """Apparent power units."""

    VOLT_AMPERE = "VA"


@register_unit
class UnitOfElectricCurrent(StrEnum):
    """Electric current units."""

    MILLIAMPERE = "mA"
    AMPERE = "A"


# Electric_potential units
@register_unit
class UnitOfElectricPotential(StrEnum):
    """Electric potential units."""

    MILLIVOLT = "mV"
    VOLT = "V"


@register_unit
class UnitOfFrequency(StrEnum):
    """Frequency units."""

    HERTZ = "Hz"
    KILOHERTZ = "kHz"
    MEGAHERTZ = "MHz"
    GIGAHERTZ = "GHz"


@register_unit
class UnitOfVolumeFlowRate(StrEnum):
    """Volume flow rate units."""

    CUBIC_METERS_PER_HOUR = "m³/h"
    CUBIC_FEET_PER_MINUTE = "ft³/min"
    LITERS_PER_MINUTE = "L/min"
    GALLONS_PER_MINUTE = "gal/min"


@register_unit
class UnitOfVolume(StrEnum):
    """Volume units."""

    CUBIC_FEET = "ft³"
    CENTUM_CUBIC_FEET = "CCF"
    CUBIC_METERS = "m³"
    LITERS = "L"
    MILLILITERS = "mL"
    GALLONS = "gal"
    """Assumed to be US gallons in conversion utilities.

    British/Imperial gallons are not yet supported"""
    FLUID_OUNCES = "fl. oz."
    """Assumed to be US fluid ounces in conversion utilities.

    British/Imperial fluid ounces are not yet supported"""


@register_unit
class UnitOfTime(StrEnum):
    """Time units."""

    MICROSECONDS = "μs"
    MILLISECONDS = "ms"
    SECONDS = "s"
    MINUTES = "min"
    HOURS = "h"
    DAYS = "d"
    WEEKS = "w"
    MONTHS = "m"
    YEARS = "y"


@register_unit
class UnitOfEnergy(StrEnum):
    """Energy units."""

    JOULE = "J"
    KILO_JOULE = "kJ"
    MEGA_JOULE = "MJ"
    GIGA_JOULE = "GJ"
    WATT_HOUR = "Wh"
    KILO_WATT_HOUR = "kWh"
    MEGA_WATT_HOUR = "MWh"
    CALORIE = "cal"
    KILO_CALORIE = "kcal"
    MEGA_CALORIE = "Mcal"
    GIGA_CALORIE = "Gcal"


# Concentration units
@register_unit
class UnitOfVolumetricFlux(StrEnum):
    """Volumetric flux, commonly used for precipitation intensity.

    The derivation of these units is a volume of rain amassing in a container
    with constant cross section in a given time
    """

    INCHES_PER_DAY = "in/d"
    """Derived from in³/(in²⋅d)"""

    INCHES_PER_HOUR = "in/h"
    """Derived from in³/(in²⋅h)"""

    MILLIMETERS_PER_DAY = "mm/d"
    """Derived from mm³/(mm²⋅d)"""

    MILLIMETERS_PER_HOUR = "mm/h"
    """Derived from mm³/(mm²⋅h)"""


@register_unit
class UnitOfSignalStrength(StrEnum):
    """Signal strength."""

    DECIBELS = "dB"
    DECIBELS_MILLIWATT = "dBm"


@register_unit
class UnitOfIlluminance(StrEnum):
    """Illuminance."""

    LUX = "lx"


@register_unit
class UnitOfCurrency(StrEnum):
    """Currency."""

    EURO = "€"
    DOLLAR = "$"
    CENT = "¢"


@register_unit
class UnitOfLength(StrEnum):
    """Length units."""

    MILLIMETERS = "mm"
    CENTIMETERS = "cm"
    METERS = "m"
    KILOMETERS = "km"
    INCHES = "in"
    FEET = "ft"
    YARDS = "yd"
    MILES = "mi"
    NAUTICAL_MILES = "nmi"


@register_unit
class UnitOfIrradiance(StrEnum):
    """Irradiance units."""

    WATTS_PER_SQUARE_METER = "W/m²"
    BTUS_PER_HOUR_SQUARE_FOOT = "BTU/(h⋅ft²)"


@register_unit
class UnitOfPrecipitationDepth(StrEnum):
    """Precipitation depth.

    The derivation of these units is a volume of rain amassing in a container
    with constant cross section
    """

    INCHES = "in"
    """Derived from in³/in²"""

    MILLIMETERS = "mm"
    """Derived from mm³/mm²"""

    CENTIMETERS = "cm"
    """Derived from cm³/cm²"""


@register_unit
class UnitOfConcentration(StrEnum):
    """Concentration units."""

    MICROGRAMS_PER_CUBIC_METER = "µg/m³"
    MILLIGRAMS_PER_CUBIC_METER = "mg/m³"
    MICROGRAMS_PER_CUBIC_FOOT = "μg/ft³"
    PARTS_PER_CUBIC_METER = "p/m³"
    PARTS_PER_MILLION = "ppm"
    PARTS_PER_BILLION = "ppb"


@register_unit
class UnitOfSpeed(StrEnum):
    """Speed units."""

    BEAUFORT = "Beaufort"
    FEET_PER_SECOND = "ft/s"
    INCHES_PER_SECOND = "in/s"
    METERS_PER_SECOND = "m/s"
    KILOMETERS_PER_HOUR = "km/h"
    KNOTS = "kn"
    MILES_PER_HOUR = "mph"
    MILLIMETERS_PER_SECOND = "mm/s"


@register_unit
class UnitOfRotationalSpeed(StrEnum):
    """Rotational speed units."""

    REVOLUTIONS_PER_MINUTE = "rpm"
