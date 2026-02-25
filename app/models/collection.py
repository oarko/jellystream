from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class Collection(Base):
    __tablename__ = "collections"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    jellyfin_id = Column(String(255), nullable=True)   # set when imported from a Jellyfin boxset
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now())
