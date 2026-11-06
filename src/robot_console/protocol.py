"""Encodage des trames envoyées au récepteur WiFi du robot (ESP8266).

Une trame fait 12 octets : trois entiers 32 bits signés big-endian,
dans l'ordre [avant/arrière][translation][rotation].
"""

import struct

from robot_console.instructions import Axis

FRAME_FORMAT = ">iii"

# Position de chaque axe dans la trame.
AXIS_SLOT = {
    Axis.FORWARD: 0,
    Axis.TRANSLATION: 1,
    Axis.ROTATION: 2,
}


def encode_frame(forward: int = 0, translation: int = 0, rotation: int = 0) -> bytes:
    """Encode les trois commandes en une trame de 12 octets."""
    return struct.pack(FRAME_FORMAT, forward, translation, rotation)


def encode_move(axis: Axis, intensity: int) -> bytes:
    """Encode une commande sur un seul axe, les autres restant à zéro."""
    values = [0, 0, 0]
    values[AXIS_SLOT[axis]] = intensity
    return encode_frame(*values)


STOP_FRAME = encode_frame()
