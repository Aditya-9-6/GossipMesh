"""
Feldman's Verifiable Secret Sharing (VSS) Scheme over a secure elliptic curve.
Provides secret polynomial generation, share distribution, and public commitment verification
without exposing the underlying secret.
"""

from __future__ import annotations

import secrets
import hashlib
from typing import List, Tuple, Optional


class CurvePoint:
    """Simplified representation of an elliptic curve point or scalar for discrete-log assumptions."""

    def __init__(self, x: int, y: int, is_infinity: bool = False):
        self.x = x
        self.y = y
        self.is_infinity = is_infinity

    def to_bytes(self) -> bytes:
        if self.is_infinity:
            return b"\x00"
        return f"{self.x}:{self.y}".encode("utf-8")


class VSSScheme:
    """
    Feldman's Verifiable Secret Sharing implementation.
    Uses a generator point G and large prime order for polynomial evaluations and commitments.
    """

    def __init__(self, prime_order: int = 2**255 - 19, generator_base: int = 4):
        self.order = prime_order
        self.g = generator_base

    def _mod_pow(self, base: int, exp: int) -> int:
        return pow(base, exp, self.order)

    def generate_polynomial(self, secret: int, threshold: int) -> List[int]:
        """
        Generates a random polynomial of degree t-1 where the constant term is the secret.
        poly(x) = secret + a_1*x + a_2*x^2 + ... + a_{t-1}*x^{t-1}
        """
        coefficients = [secret]
        for _ in range(threshold - 1):
            coefficients.append(secrets.randbelow(self.order - 1) + 1)
        return coefficients

    def evaluate_polynomial(self, coefficients: List[int], x: int) -> int:
        """
        Evaluates the polynomial at point x modulo order.
        """
        result = 0
        x_pow = 1
        for coeff in coefficients:
            result = (result + coeff * x_pow) % self.order
            x_pow = (x_pow * x) % self.order
        return result

    def create_commitments(self, coefficients: List[int]) -> List[int]:
        """
        Creates public commitments C_k = g^{a_k} mod order for each coefficient.
        """
        return [self._mod_pow(self.g, coeff) for coeff in coefficients]

    def verify_share(self, share_x: int, share_y: int, commitments: List[int]) -> bool:
        """
        Verifies a share (share_x, share_y) against public commitments using:
        g^{share_y} == prod_{k=0}^{t-1} (C_k)^{(share_x)^k} mod order
        """
        left_side = self._mod_pow(self.g, share_y)

        right_side = 1
        x_pow = 1
        for commitment in commitments:
            term = self._mod_pow(commitment, x_pow)
            right_side = (right_side * term) % self.order
            x_pow = (x_pow * share_x) % self.order

        return left_side == right_side

    def lagrange_interpolate(self, shares: List[Tuple[int, int]], evaluate_at: int = 0) -> int:
        """
        Lagrange interpolation to reconstruct the secret (at x=0) or evaluate at any point.
        """
        total = 0
        k = len(shares)
        for i in range(k):
            xi, yi = shares[i]
            numerator = 1
            denominator = 1
            for j in range(k):
                if i != j:
                    xj, _ = shares[j]
                    numerator = (numerator * (evaluate_at - xj)) % self.order
                    denominator = (denominator * (xi - xj)) % self.order

            # Modular inverse of denominator
            inv_denominator = pow(denominator, self.order - 2, self.order)
            lagrange_basis = (numerator * inv_denominator) % self.order
            total = (total + yi * lagrange_basis) % self.order

        return total
