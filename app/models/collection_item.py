from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func

from app.core.database import Base


class CollectionItem(Base):
    """
    One media item belonging to a Collection.

    Field layout mirrors ScheduleEntry (minus time fields) so that in Phase 2
    a Collection can serve as a content source for channel schedule generation
    without a schema migration.
    """
    __tablename__ = "collection_items"

    id             = Column(Integer, primary_key=True, index=True)
    collection_id  = Column(
        Integer,
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Jellyfin identity
    media_item_id  = Column(String(255), nullable=False)   # Jellyfin item ID
    item_type      = Column(String(50),  nullable=False)   # "Movie"|"Series"|"Season"|"Episode"
    library_id     = Column(String(255), nullable=False)   # Jellyfin library/view ID

    # Titles
    title          = Column(String(255), nullable=False)
    series_name    = Column(String(255), nullable=True)
    season_number  = Column(Integer,     nullable=True)
    episode_number = Column(Integer,     nullable=True)

    # Scheduling data (Phase 2)
    duration       = Column(Integer, nullable=True)   # seconds

    # Metadata from NFO sidecars
    genres         = Column(Text, nullable=True)       # JSON array string
    description    = Column(Text, nullable=True)
    content_rating = Column(String(20), nullable=True)
    air_date       = Column(String(20), nullable=True)  # "YYYY" or "YYYY-MM-DD"

    # File locations
    file_path      = Column(Text, nullable=True)        # local path (verify + Phase 2 seek)
    thumbnail_path = Column(Text, nullable=True)        # local .jpg sidecar path

    sort_order     = Column(Integer, default=0)
    created_at     = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_collection_items_collection_type", "collection_id", "item_type"),
    )
