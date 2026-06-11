from sqlalchemy import Column, Index, String, Integer, DateTime, func, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base

class Brand(Base):
    __tablename__ = "brands"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    owner_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
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
    
    # Relationship
    brand = relationship("Brand", back_populates="profile")

class BrandVoiceRule(Base):
    __tablename__ = "brand_voice_rules"
    
    id = Column(String, primary_key=True)
    brand_id = Column(String, ForeignKey("brands.id"), nullable=False, index=True)
    rule_type = Column(String, nullable=False)  # forbidden_word, tone_pattern, cta_pattern
    value = Column(String, nullable=False)
    
    # Composite index
    __table_args__ = (
        Index("idx_brand_rule_type", "brand_id", "rule_type"),
    )
    
    brand = relationship("Brand", back_populates="voice_rules")

class BrandMessaging(Base):
    __tablename__ = "brand_messaging"
    
    id = Column(String, primary_key=True)
    brand_id = Column(String, ForeignKey("brands.id"), nullable=False, index=True)
    message_type = Column(String, nullable=False)  # pain_point, objection, proof_point
    value = Column(String, nullable=True)  # For pain_point, proof_point
    parent_id = Column(String, ForeignKey("brand_messaging.id"), nullable=True)  # For objection nesting
    objection = Column(String, nullable=True)  # For objection type
    counter = Column(String, nullable=True)  # For objection counter
    
    __table_args__ = (
        Index("idx_brand_message_type", "brand_id", "message_type"),
    )
    
    brand = relationship("Brand", back_populates="messaging")

class BrandContentExample(Base):
    __tablename__ = "brand_content_examples"
    
    id = Column(String, primary_key=True)
    brand_id = Column(String, ForeignKey("brands.id"), nullable=False, index=True)
    example_type = Column(String, nullable=False)  # blog_post, social_post, ad_copy, landing_page
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    url = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index("idx_brand_example_type", "brand_id", "example_type"),
    )
    
    brand = relationship("Brand", back_populates="examples")