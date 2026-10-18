import secrets
from typing import List, Tuple

# Standard prime order for a simplified elliptic curve group or scalar field (secp256k1 order)
CURVE_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
CURVE_GENERATOR_X = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
CURVE_GENERATOR_Y = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8


def mod_inverse(k: int, mod: int) -> int:
    """Return modular inverse of k modulo mod using extended Euclidean algorithm."""
    if k == 0:
        raise ZeroDivisionError('division by zero')
    return pow(k, mod - 2, mod)


class Point:
    """Simplified elliptic curve point representation for discrete-log cryptographic primitives."""
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __eq__(self, other: 'Point') -> bool:
        return self.x == other.x and self.y == other.y

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"


# Base generator point
G = Point(CURVE_GENERATOR_X, CURVE_GENERATOR_Y)


def point_add(p1: Point, p2: Point) -> Point:
    """Simplified point addition over secp256k1 field."""
    if p1.x == 0 and p1.y == 0:
        return p2
    if p2.x == 0 and p2.y == 0:
        return p1
    if p1.x == p2.x:
        if (p1.y + p2.y) % CURVE_ORDER == 0:
            return Point(0, 0)
        return point_double(p1)
    
    lam = (p2.y - p1.y) * mod_inverse((p2.x - p1.x) % CURVE_ORDER, CURVE_ORDER) % CURVE_ORDER
    x3 = (lam * lam - p1.x - p2.x) % CURVE_ORDER
    y3 = (lam * (p1.x - x3) - p1.y) % CURVE_ORDER
    return Point(x3, y3)


def point_double(p: Point) -> Point:
    """Point doubling."""
    if p.y == 0:
        return Point(0, 0)
    lam = (3 * p.x * p.x) * mod_inverse((2 * p.y) % CURVE_ORDER, CURVE_ORDER) % CURVE_ORDER
    x3 = (lam * lam - 2 * p.x) % CURVE_ORDER
    y3 = (lam * (p.x - x3) - p.y) % CURVE_ORDER
    return Point(x3, y3)


def scalar_mult(k: int, p: Point) -> Point:
    """Scalar multiplication using double-and-add algorithm."""
    result = Point(0, 0)
    addend = p
    k = k % CURVE_ORDER
    while k > 0:
        if k & 1:
            result = point_add(result, addend)
        addend = point_double(addend)
        k >>= 1
    return result


class VerifiableSecretSharing:
    """Feldman's Verifiable Secret Sharing Scheme over elliptic curve."""
    @staticmethod
    def generate_polynomial(secret: int, threshold: int) -> List[int]:
        """Generates random polynomial coefficients where a_0 is the secret and degree is threshold - 1 (length is threshold)."""
        coeffs = [secret]
        for _ in range(threshold - 1):
            coeffs.append(secrets.randbelow(CURVE_ORDER - 1) + 1)
        return coeffs

    @staticmethod
    def evaluate_polynomial(coeffs: List[int], x: int) -> int:
        """Evaluates polynomial at x using Horner's method."""
        res = 0
        for coeff in reversed(coeffs):
            res = (res * x + coeff) % CURVE_ORDER
        return res

    @classmethod
    def commit(cls, coeffs: List[int]) -> List[Point]:
        """Computes Feldman commitments: C_j = a_j * G."""
        return [scalar_mult(coeff, G) for coeff in coeffs]

    @classmethod
    def verify_share(cls, share_x: int, share_y: int, commitments: List[Point]) -> bool:
        """Verifies share (share_x, share_y) against commitments C."""
        lhs = scalar_mult(share_y, G)
        rhs = Point(0, 0)
        x_pow = 1
        for c in commitments:
            term = scalar_mult(x_pow, c)
            rhs = point_add(rhs, term)
            x_pow = (x_pow * share_x) % CURVE_ORDER
        return lhs == rhs
