from typing import Annotated
from uuid import UUID

from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter, Query

from rest_api.dependencies import ContractorUser, CurrentUser, Language
from schemas.offers.sch_offer import MyOffersFilterSchema, MyOffersPageSchema, OfferCreateSchema, OfferSchema
from services.offers.svc_offers import OfferService

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("/mine")
@inject
async def list_my_offers(
    filters: Annotated[MyOffersFilterSchema, Query()],
    user: ContractorUser,
    language: Language,
    svc_offers: Injected[OfferService],
) -> MyOffersPageSchema:
    return await svc_offers.list_my_offers(user, filters, language)


@router.put("/{offer_id}")
@inject
async def update_offer(
    offer_id: UUID, body: OfferCreateSchema, user: ContractorUser, svc_offers: Injected[OfferService]
) -> OfferSchema:
    return await svc_offers.update_offer(user, offer_id, body)


@router.post("/{offer_id}/withdraw")
@inject
async def withdraw_offer(offer_id: UUID, user: ContractorUser, svc_offers: Injected[OfferService]) -> OfferSchema:
    return await svc_offers.withdraw_offer(user, offer_id)


@router.post("/{offer_id}/accept")
@inject
async def accept_offer(offer_id: UUID, user: CurrentUser, svc_offers: Injected[OfferService]) -> OfferSchema:
    return await svc_offers.accept_offer(user, offer_id)
