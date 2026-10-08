import contextlib
from collections.abc import AsyncIterator

from aioinject.ext.fastapi import AioInjectMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from common.database import engine
from models import import_all_models
from rest_api.error_handlers import register_error_handlers
from rest_api.routers import api_v1_router
from services.di.container import create_container
from settings.app_settings import AppSettings
from settings.keycloak_settings import KeycloakSettings
from settings.resolver import get_settings


def _operation_id(route: APIRoute) -> str:
    """Endpoint function name becomes the Orval hook name: get_health -> useGetHealth."""
    return route.name


@contextlib.asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with create_container():
        yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings(AppSettings)
    keycloak_settings = get_settings(KeycloakSettings)
    import_all_models()

    app = FastAPI(
        title="Sheber API",
        version="0.1.0",
        debug=settings.debug,
        lifespan=_lifespan,
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        generate_unique_id_function=_operation_id,
        swagger_ui_oauth2_redirect_url="/api/docs/oauth2-redirect",
        swagger_ui_init_oauth={
            "clientId": keycloak_settings.swagger_client_id,
            "usePkceWithAuthorizationCodeGrant": True,
            "scopes": "openid",
        },
    )
    app.add_middleware(AioInjectMiddleware, container=create_container())
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(api_v1_router)
    return app
