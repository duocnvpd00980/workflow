from sqlalchemy import Column, Index, String, Integer, DateTime, func, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base
from app.business.models import Business

class Brand(Base):
    __tablename__ = "brands"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    owner_id = Column(String, nullable=False, index=True)

    # ── Link về Business ─────────────────────────────────────────
    business_id = Column(String, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=True, index=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    business = relationship("Business", back_populates="brands")
    profile = relationship("BrandProfile", back_populates="brand", uselist=False, cascade="all, delete-orphan")
    voice_rules = relationship("BrandVoiceRule", back_populates="brand", cascade="all, delete-orphan")
    messaging = relationship("BrandMessaging", back_populates="brand", cascade="all, delete-orphan")
    examples = relationship("BrandContentExample", back_populates="brand", cascade="all, delete-orphan")

class BrandProfile(Base):
    __tablename__ = "brand_profiles"
    
    brand_id = Column(String, ForeignKey("brands.id"), primary_key=True)
    positioning = Column(String, nullable=False)
    audience = Column(String, nullable=False)
    visual_identity = Column(JSON, nullable=False)  # {style_description, color_palette, mood}
    version = Column(Integer, default=1)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    mined_at = Column(DateTime, nullable=True)
    
    brand = relationship("Brand", back_populates="profile")

class BrandVoiceRule(Base):
    __tablename__ = "brand_voice_rules"
    
    id = Column(String, primary_key=True)
    brand_id = Column(String, ForeignKey("brands.id"), nullable=False, index=True)
    rule_type = Column(String, nullable=False)  # forbidden_word, tone_pattern, cta_pattern
    value = Column(String, nullable=False)
    
    __table_args__ = (
        Index("idx_brand_rule_type", "brand_id", "rule_type"),
    )
    
    brand = relationship("Brand", back_populates="voice_rules")

class BrandMessaging(Base):
    __tablename__ = "brand_messaging"
    
    id = Column(String, primary_key=True)
    brand_id = Column(String, ForeignKey("brands.id"), nullable=False, index=True)
    message_type = Column(String, nullable=False)  # pain_point, objection, proof_point
    value = Column(String, nullable=True)
    parent_id = Column(String, ForeignKey("brand_messaging.id"), nullable=True)
    objection = Column(String, nullable=True)
    counter = Column(String, nullable=True)
    
    __table_args__ = (
        Index("idx_brand_message_type", "brand_id", "message_type"),
    )
    
    brand = relationship("Brand", back_populates="messaging")

class BrandContentExample(Base):
    __tablename__ = "brand_content_examples"
    
    id = Column(String, primary_key=True)
    brand_id = Column(String, ForeignKey("brands.id"), nullable=False, index=True)
    example_type = Column(String, nullable=False)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    url = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index("idx_brand_example_type", "brand_id", "example_type"),
    )
    
    brand = relationship("Brand", back_populates="examples")


