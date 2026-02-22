"""GenreFilter model — genre-based content filter for a channel."""

from sqlalchemy import Column, Integer, String, ForeignKey

from app.core.database import Base


class GenreFilter(Base):
    """
    A genre filter applied when auto-generating a channel's schedule.

    Each filter specifies a genre name and whether to include movies,
    episodes, or both. Multiple filters on a channel are additive (OR logic).
    """

    __tablename__ = "genre_filters"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(
        Integer,
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    genre = Column(String(100), nullable=False)    # e.g. "Sci-Fi", "Horror", "Action"
    content_type = Column(String(20), default="both")  # "movie" | "episode" | "both"
