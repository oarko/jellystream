"""ChannelLibrary model — join table linking channels to Jellyfin libraries."""

from sqlalchemy import Column, Integer, String, ForeignKey

from app.core.database import Base


class ChannelLibrary(Base):
    """
    Associates a channel with a Jellyfin library.

    A single channel can pull content from multiple libraries
    (e.g., a Sci-Fi channel drawing from both a Movies and TV Shows library).
    """

    __tablename__ = "channel_libraries"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(
        Integer,
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    library_id = Column(String(255), nullable=False)     # Jellyfin library/view ID
    library_name = Column(String(255), nullable=False)   # Cached display name
    collection_type = Column(String(50), nullable=False) # "movies" | "tvshows" | "mixed"
