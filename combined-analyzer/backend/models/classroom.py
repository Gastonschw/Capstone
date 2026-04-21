"""
Class and ClassMember models for teacher/student classes.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Class(Base):
    """Represents a logical class created by a teacher/admin."""

    __tablename__ = "classes"

    # Supabase Postgres uses gen_random_uuid() as a server-side default
    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    owner_user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    join_code = Column(String(20), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    members = relationship(
        "ClassMember",
        back_populates="class_",
        cascade="all, delete-orphan",
    )
    admins = relationship(
        "ClassAdmin",
        back_populates="class_",
        cascade="all, delete-orphan",
    )


class ClassAdmin(Base):
    """Additional admin (teacher) of a class beyond the creator.

    The creator is tracked by ``Class.owner_user_id``. This table is only for
    admins that were explicitly promoted from the class roster.
    """

    __tablename__ = "class_admins"
    __table_args__ = (
        UniqueConstraint("class_id", "user_id", name="uq_class_admins_class_user"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    class_id = Column(PG_UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    class_ = relationship("Class", back_populates="admins")


class ClassMember(Base):
    """Membership of a user in a class."""

    __tablename__ = "class_members"
    __table_args__ = (
        UniqueConstraint("class_id", "user_id", name="uq_class_members_class_user"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    class_id = Column(PG_UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    class_ = relationship("Class", back_populates="members")

