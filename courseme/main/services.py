import collections

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import load_only

from courseme import db
from courseme.models import Objective, User, Topic, ROLE_ADMIN


CMContext = collections.namedtuple('CMContext', ['user'])


def cm():
    """Automatically create a CMContext from the implicitly scoped Flask context
    """

    from flask import has_request_context, g

    if not has_request_context():
        raise ValueError(
            "Cannot automatically create a new CMContext without an implicitly "
            "scoped flash RequestContext.  A CMContext can be constructed "
            "manually if desired")

    return CMContext(user=g.user)


def _validate_prerequisites(names, subject_id, user):
    names = names if names else []
    prerequisites = Objective.query.filter(
        Objective.subject_id == subject_id,     # and_
        Objective.name.in_(names),              # and_
        or_(
            Objective.created_by_id.in_(
                User.admin_usersQ().options(load_only("id"))),
            Objective.created_by_id == user.id)).all()

    if not set(names) <= set(o.name for o in prerequisites):
        diff = set(names) - set(o.name for o in prerequisites)
        raise ValueError(u"Given pre-requisites are not available: {}".format(
            u', '.join(diff)))

    return prerequisites


class ObjectiveService(object):

    def __init__(self, context):
        self._context = context

    def create(self,
               name,
               subject_id,
               topic_id=None,
               description=None,
               assessable=None,
               prerequisite_names=None):
        """Create a new Objective, associated with the given Subject

        :param subject: the Subject associated with the new Objective
        :param name: unicode name of the new Objective
        :param description: optional unicode description
        :param assessable: optional boolean
        :param prerequisites: optional list of `Objective`s.
        """

        # if topic_id is not None:
        topic = Topic.query.get(topic_id)

        if topic is not None and topic.subject_id != subject_id:
            raise ValueError("Topic's subject must match the new Objective's subject")

        prerequisites = _validate_prerequisites(prerequisite_names, subject_id, self._context.user)

        objective = Objective(name=name,
                              subject_id=subject_id,
                              topic_id=topic_id,
                              prerequisites=prerequisites,
                              created_by_id=self._context.user.id)

        db.session.add(objective)
        db.session.commit()
        return objective

    def update(self,
               objective_id,
               name,
               prerequisite_names,
               topic_id):

        objective = Objective.query.get(objective_id)
        if objective is None:
            raise NotFound(Objective, objective_id)

        if self._context.user.role != ROLE_ADMIN and objective.created_by_id != self._context.user.id:
            raise AuthorizationError("You do not have permission to edit this Objective")

        if name != objective.name:
            pass    # do in form

        topic = Topic.query.get(topic_id)

        if self._context.user.subject_id != objective.subject_id:
            raise ValueError(
                "User attempting to edit an Objective while within the context of "
                "another Subject")

        if topic and topic.subject_id != objective.subject_id:
            raise ValueError("Topic's subject must match Objective's subject")

        prerequisites = _validate_prerequisites(prerequisite_names, objective.subject_id, self._context.user)

        cyclic_prerequisites = [
            p.name for p in prerequisites if p.is_required_indirect(objective)]

        if cyclic_prerequisites:
            # TODO: this probably needs to be presented to the User
            raise ValidationError("todo")

        objective.name = name
        objective.prerequisites = prerequisites
        objective.topic_id = topic_id
        objective.last_updated = datetime.utcnow()
        db.session.add(objective)
        db.session.commit()
        return objective
