from sqlalchemy import Column, Integer, String, ForeignKey
from app.core.database import Base


class ChannelCollectionSource(Base):
    """Links a channel to a JellyStream collection as a content source."""
    __tablename__ = "channel_collection_sources"

    id              = Column(Integer, primary_key=True, index=True)
    channel_id      = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id   = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False)
    collection_name = Column(String(255), nullable=False)  # cached for display
