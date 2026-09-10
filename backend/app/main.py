from app.core.app import app
from app.features.health.routes import router as health_router

# Health stays at the root (no version prefix) so probes have a stable URL.
# Other features can add versioned routers here, e.g. APIRouter(prefix="/v1").
app.include_router(health_router)
