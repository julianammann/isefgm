"""Aggregates all v1 routers under `/api/v1`. Register every new domain router here."""

from fastapi import APIRouter

from giftmanager.api.v1 import auth, giftings, gifts, health, links, notes, occasions, people

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(people.router)
router.include_router(occasions.types_router)
router.include_router(occasions.router)
router.include_router(gifts.router)
router.include_router(giftings.router)
router.include_router(notes.router)
router.include_router(links.router)
