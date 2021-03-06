from .. import db
from purchase import CartItem
from sqlalchemy import or_, desc, func
from ..models import Vendor, User
from sqlalchemy import UniqueConstraint


class Tag(db.Model):
    __tablename__ = "tag"
    id = db.Column(db.Integer, primary_key=True)
    tag_name = db.Column(db.String(1000))
    vendors = db.relationship("TagAssociation", back_populates="tag")


class TagAssociation(db.Model):
    __tablename__ = "tagassociation"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'))
    tag = db.relationship("Tag", back_populates="vendors")
    vendor = db.relationship("Vendor", back_populates="tags")

class ItemTag(db.Model):
    __tablename__ = "itemtag"
    id = db.Column(db.Integer, primary_key=True)
    item_tag_name = db.Column(db.String(64))
    tag_color = db.Column(db.String(64))
