# Based on the excellent work by https://github.com/nikidigi/pithouse2boxflat

import json


class PithouseConverter:
    """Converts Moza Pithouse presets to boxflat/foxblat format."""

    def validate(self, pithouse_data: dict) -> tuple[bool, str]:
        """Validate Pithouse preset structure.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(pithouse_data, dict):
            return False, "Invalid preset format: expected JSON object"

        if pithouse_data.get("deviceType") != "Motor":
            device_type = pithouse_data.get("deviceType", "unknown")
            return False, f"Unsupported device type '{device_type}'. Only wheel bases are supported."

        device_params = pithouse_data.get("deviceParams")
        if not device_params:
            return False, "Missing deviceParams in preset"

        if device_params.get("version") != 2:
            version = device_params.get("version", "unknown")
            return False, f"Unsupported deviceParams version '{version}'. Only v2 is supported."

        return True, ""

    def get_preset_name(self, pithouse_data: dict) -> str:
        """Extract preset name from Pithouse data."""
        return pithouse_data.get("name", "imported-preset")

    def convert(self, pithouse_data: dict) -> dict:
        """Convert Pithouse preset to boxflat format.

        Args:
            pithouse_data: Parsed Pithouse preset JSON

        Returns:
            Boxflat preset dictionary ready to be saved as YAML
        """
        device_params = pithouse_data["deviceParams"]

        return {
            "FoxblatPresetVersion": "1",
            "base": self._convert_base(device_params),
            "main": self._convert_main(device_params),
        }

    def _convert_base(self, device_params: dict) -> dict:
        """Convert deviceParams to base settings."""
        base = {
            "ffb-reverse": 1 if device_params.get("gameForceFeedbackReversal") else 0,
            "ffb-strength": device_params.get("gameForceFeedbackStrength", 0) * 10,
            "max-angle": device_params.get("maximumSteeringAngle", 900),
            "protection": 1 if device_params.get("safeDrivingEnabled") else 0,
            "protection-mode": device_params.get("safeDrivingMode", 0),
            "soft-limit-retain": device_params.get("softLimitGameForceStrength", 0),
            "soft-limit-stiffness": device_params.get("softLimitStiffness", 0),
            "soft-limit-strength": device_params.get("softLimitStrength", 0),
            "speed-damping": device_params.get("speedDependentDamping", 0),
            "speed-damping-point": device_params.get("initialSpeedDependentDamping", 0),
            "equalizer1": device_params.get("equalizerGain1", 50),
            "equalizer2": device_params.get("equalizerGain2", 50),
            "equalizer3": device_params.get("equalizerGain3", 50),
            "equalizer4": device_params.get("equalizerGain4", 50),
            "equalizer5": device_params.get("equalizerGain5", 50),
            "equalizer6": device_params.get("equalizerGain6", 50),
            "damper": device_params.get("mechanicalDamper", 0) * 10,
            "friction": device_params.get("mechanicalFriction", 0) * 10,
            "inertia": device_params.get("naturalInertiaV2", 0) * 10,
            "spring": device_params.get("mechanicalSpringStrength", 0) * 10,
            "speed": device_params.get("maximumSteeringSpeed", 0) * 10,
            "limit": device_params.get("maximumSteeringAngle") or device_params.get("maximumGameSteeringAngle", 900),
            "torque": device_params.get("maximumTorque", 100),
            # Default values for fields not in Pithouse presets
            "natural-inertia": 0,
            "road-sensitivity": 0,
        }

        # Add FFB curve points
        ffb_curve = self._decode_ffb_curve(device_params.get("forceFeedbackMaping", ""))
        base.update(ffb_curve)

        return base

    def _convert_main(self, device_params: dict) -> dict:
        """Convert deviceParams to main settings."""
        return {
            "set-damper-gain": min(round(2.55 * device_params.get("setGameDampingValue", 0)), 255),
            "set-friction-gain": min(round(2.55 * device_params.get("setGameFrictionValue", 0)), 255),
            "set-inertia-gain": min(round(2.55 * device_params.get("setGameInertiaValue", 0)), 255),
            "set-spring-gain": min(round(2.55 * device_params.get("setGameSpringValue", 0)), 255),
            "set-interpolation": device_params.get("constForceExtraMode", 0),
        }

    def _decode_ffb_curve(self, mapping: str) -> dict:
        """Decode FFB curve from Pithouse forceFeedbackMaping string.

        The mapping is a string where each character's code represents a curve point.
        """
        if not mapping or len(mapping) < 12:
            # Return default linear curve if mapping is invalid
            return {
                "ffb-curve-x1": 20,
                "ffb-curve-y1": 20,
                "ffb-curve-y2": 40,
                "ffb-curve-y3": 60,
                "ffb-curve-y4": 80,
                "ffb-curve-y5": 100,
            }

        curve = [ord(c) for c in mapping]

        return {
            "ffb-curve-x1": curve[2],
            "ffb-curve-y1": curve[3],
            "ffb-curve-y2": curve[5],
            "ffb-curve-y3": curve[7],
            "ffb-curve-y4": curve[9],
            "ffb-curve-y5": curve[11],
        }

    def load_and_convert(self, filepath: str) -> tuple[dict | None, str, str]:
        """Load a Pithouse preset file and convert it.

        Args:
            filepath: Path to the Pithouse .json preset file

        Returns:
            Tuple of (converted_preset, preset_name, error_message)
            If successful, error_message is empty.
            If failed, converted_preset is None.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                pithouse_data = json.load(f)
        except json.JSONDecodeError as e:
            return None, "", f"Invalid JSON: {e}"
        except OSError as e:
            return None, "", f"Failed to read file: {e}"

        is_valid, error = self.validate(pithouse_data)
        if not is_valid:
            return None, "", error

        preset_name = self.get_preset_name(pithouse_data)
        converted = self.convert(pithouse_data)

        return converted, preset_name, ""
