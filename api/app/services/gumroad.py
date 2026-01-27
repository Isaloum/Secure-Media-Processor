"""Gumroad service for license validation"""

from typing import Optional

import httpx

from app.config import settings


class GumroadService:
    """Service for Gumroad license verification"""

    BASE_URL = "https://api.gumroad.com/v2"

    def __init__(self):
        self.api_key = settings.gumroad_api_key
        self.product_id = settings.gumroad_product_id

    async def verify_license(
        self,
        license_key: str,
        product_id: Optional[str] = None,
        increment_uses: bool = True,
    ) -> dict:
        """
        Verify a Gumroad license key

        Returns:
            dict with keys:
                - valid: bool
                - tier: str (free, pro, enterprise)
                - email: str (buyer email)
                - sale_id: str
                - uses: int
                - message: str
        """
        if not self.api_key:
            # If no API key configured, return invalid
            return {
                "valid": False,
                "tier": "free",
                "message": "License validation not configured",
            }

        url = f"{self.BASE_URL}/licenses/verify"
        data = {
            "product_id": product_id or self.product_id,
            "license_key": license_key,
            "increment_uses_count": str(increment_uses).lower(),
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=data, timeout=10.0)
                result = response.json()

                if not result.get("success"):
                    return {
                        "valid": False,
                        "tier": "free",
                        "message": result.get("message", "Invalid license key"),
                    }

                purchase = result.get("purchase", {})

                # Determine tier from product variants or custom fields
                tier = self._determine_tier(purchase)

                return {
                    "valid": True,
                    "tier": tier,
                    "email": purchase.get("email"),
                    "sale_id": purchase.get("sale_id"),
                    "uses": result.get("uses", 0),
                    "product_name": purchase.get("product_name"),
                    "refunded": purchase.get("refunded", False),
                    "disputed": purchase.get("disputed", False),
                    "message": "License verified successfully",
                }

        except httpx.TimeoutException:
            return {
                "valid": False,
                "tier": "free",
                "message": "License verification timed out",
            }
        except Exception as e:
            return {
                "valid": False,
                "tier": "free",
                "message": f"License verification failed: {str(e)}",
            }

    def _determine_tier(self, purchase: dict) -> str:
        """Determine license tier from purchase data"""
        # Check for refunded or disputed
        if purchase.get("refunded") or purchase.get("disputed"):
            return "free"

        # Check product variants
        variants = purchase.get("variants", {})
        variant_name = list(variants.values())[0] if variants else ""

        variant_lower = variant_name.lower()
        if "enterprise" in variant_lower:
            return "enterprise"
        elif "pro" in variant_lower or "professional" in variant_lower:
            return "pro"

        # Check price (fallback method)
        price_cents = purchase.get("price", 0)
        if price_cents >= 9900:  # $99+
            return "enterprise"
        elif price_cents >= 2900:  # $29+
            return "pro"

        return "pro"  # Default for valid purchases

    async def disable_license(self, license_key: str, product_id: Optional[str] = None) -> dict:
        """Disable a license key"""
        if not self.api_key:
            return {"success": False, "message": "API key not configured"}

        url = f"{self.BASE_URL}/licenses/disable"
        data = {
            "access_token": self.api_key,
            "product_id": product_id or self.product_id,
            "license_key": license_key,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(url, data=data, timeout=10.0)
                result = response.json()

                return {
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                }
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def enable_license(self, license_key: str, product_id: Optional[str] = None) -> dict:
        """Enable a previously disabled license key"""
        if not self.api_key:
            return {"success": False, "message": "API key not configured"}

        url = f"{self.BASE_URL}/licenses/enable"
        data = {
            "access_token": self.api_key,
            "product_id": product_id or self.product_id,
            "license_key": license_key,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(url, data=data, timeout=10.0)
                result = response.json()

                return {
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                }
        except Exception as e:
            return {"success": False, "message": str(e)}


# Singleton instance
gumroad_service = GumroadService()
