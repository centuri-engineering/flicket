#! usr/bin/python3
# -*- coding: utf-8 -*-
#
# Flicket - copyright Paul Bourne: evereux@gmail.com

from flask import url_for
from flask_babel import lazy_gettext
from flask_pagedown.fields import PageDownField
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SelectField,
    HiddenField,
    SubmitField,
    FileField,
    DecimalField,
)
from wtforms.fields import SelectMultipleField
from wtforms.validators import DataRequired, Length
from wtforms.widgets import ListWidget, CheckboxInput

from application.flicket.models.flicket_models import (
    FlicketDomain,
    FlicketInstitute,
    FlicketPriority,
    FlicketRequesterRole,
    FlicketRequestType,
    FlicketProcedureStage,
    FlicketStatus,
    FlicketTicket,
    FlicketInstituteDomain,
    field_size,
)
from application.flicket.models.flicket_user import FlicketUser, user_field_size
from application.flicket.scripts.upload_choice_generator import generate_choices
from flask_babel import gettext

form_class_button = {"class": "btn btn-primary btn-sm"}
form_class_button_sm = {"class": "btn btn-primary btn-sm"}
form_danger_button = {"class": "btn btn-danger btn-sm"}


def does_email_exist(form, field):
    """
    Username must be unique so we check against the database to ensure it doesn't
    :param form:
    :param field:
    :return True / False:
    """
    if form.email.data:
        result = FlicketUser.query.filter_by(email=form.email.data).count()
        if not result:
            field.errors.append(gettext("Can't find user."))
            return False
    else:
        return False

    return True


def does_user_exist(form, field):
    """
    Username must be unique so we check against the database to ensure it doesn't
    :param form:
    :param field:
    :return True / False:
    """
    if form.username.data:
        result = FlicketUser.query.filter_by(username=form.username.data).count()
        if result == 0:
            field.errors.append(gettext("Can't find user."))
            return False
    else:
        return False

    return True


def does_institute_exist(form, field):
    """
    Username must be unique so we check against the database to ensure it doesn't
    :param form:
    :param field:
    :return True / False:
    """
    result = FlicketInstitute.query.filter_by(institute=form.institute.data).count()
    if result > 0:
        field.errors.append(gettext("Institute already exists."))
        return False

    return True


def does_domain_exist(form, field):
    """
    Username must be unique so we check against the database to ensure it doesn't
    :param form:
    :param field:
    :return True / False:
    """
    result = (
        FlicketDomain.query.filter_by(domain=form.domain.data)
        .filter_by(institute_id=form.institute_id.data)
        .count()
    )
    if result > 0:
        field.errors.append(gettext("Domain already exists."))
        return False

    return True


def does_unique_institute_domain_exist(form, field):
    """
    InstituteDomain is CONCAT of '{FlicketInstitute.institute} / {FlicketDomain.domain}'
    :param form:
    :param field:
    :return True / False:
    """
    result = FlicketInstituteDomain.query.filter_by(
        institute_domain=form.institute_domain.data
    ).count()
    if result == 0:
        field.errors.append(gettext("Domain does not exist."))
        return False
    if result > 1:
        field.errors.append(
            gettext("Ambiguous institute / domain, contact administrator to fix it!")
        )
        return False

    return True


class CreateTicketForm(FlaskForm):
    def __init__(self, *args, **kwargs):
        form = super(CreateTicketForm, self).__init__(*args, **kwargs)
        self.priority.choices = [
            (p.id, p.priority) for p in FlicketPriority.query.all()
        ]
        self.requester_role.choices = [
            (p.id, p.requester_role) for p in FlicketRequesterRole.query.all()
        ]
        self.request_type.choices = [
            (s.id, s.request_type) for s in FlicketRequestType.query.all()
        ]
        self.request_type.choices.insert(0, (0, "request type"))

        self.procedure_stage.choices = [
            (s.id, s.procedure_stage) for s in FlicketProcedureStage.query.all()
        ]
        self.procedure_stage.choices.insert(0, (0, "procedure stage"))

        self.domain.choices = [
            (c.id, "{} - {}".format(c.institute.institute, c.domain))
            for c in FlicketDomain.query.join(FlicketInstitute)
            .order_by(FlicketInstitute.institute)
            .order_by(FlicketDomain.domain)
            .all()
            if c.institute
        ]

    """ Log in form. """
    title = StringField(
        lazy_gettext("username"),
        description=lazy_gettext("Short description of the request"),
        validators=[
            DataRequired(),
            Length(
                min=field_size["title_min_length"], max=field_size["title_max_length"]
            ),
        ],
    )
    requester = StringField(
        lazy_gettext("requester"),
        description=lazy_gettext("name and contact of the requester"),
        validators=[
            DataRequired(),
            Length(
                min=field_size["title_min_length"], max=field_size["title_max_length"]
            ),
        ],
    )
    requester_role = SelectField(
        lazy_gettext("requester role"), validators=[DataRequired()], coerce=int
    )
    request_type = SelectField(
        lazy_gettext("request type"), validators=[DataRequired()], coerce=int
    )
    procedure_stage = SelectField(
        lazy_gettext("procedure stage"), validators=[DataRequired()], coerce=int
    )

    content = PageDownField(
        lazy_gettext("content"),
        validators=[
            DataRequired(),
            Length(
                min=field_size["content_min_length"],
                max=field_size["content_max_length"],
            ),
        ],
    )

    priority = SelectField(
        lazy_gettext("priority"), validators=[DataRequired()], coerce=int
    )
    domain = SelectField(
        lazy_gettext("domain"), validators=[DataRequired()], coerce=int
    )
    file = FileField(lazy_gettext("Upload Documents"), render_kw={"multiple": True})
    days = DecimalField(lazy_gettext("days"), default=0)
    submit = SubmitField(
        lazy_gettext("Submit"), render_kw=form_class_button, validators=[DataRequired()]
    )


class MultiCheckBoxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class EditTicketForm(CreateTicketForm):
    def __init__(self, ticket_id, *args, **kwargs):
        self.form = super(EditTicketForm, self).__init__(*args, **kwargs)
        # get ticket data from ticket_id
        ticket = FlicketTicket.query.filter_by(id=ticket_id).first()

        # define the multi select box for document uploads
        uploads = []
        for u in ticket.uploads:
            uploads.append((u.id, u.filename, u.original_filename))
        self.uploads.choices = []
        for x in uploads:
            uri = url_for("flicket_bp.view_ticket_uploads", filename=x[1])
            uri_label = '<a href="' + uri + '">' + x[2] + "</a>"
            self.uploads.choices.append((x[0], uri_label))

    uploads = MultiCheckBoxField("Label", coerce=int)
    submit = SubmitField(
        lazy_gettext("Edit Ticket"),
        render_kw=form_class_button,
        validators=[DataRequired()],
    )


class ReplyForm(FlaskForm):
    """ Content form. Displayed when replying too end editing tickets """

    def __init__(self, *args, **kwargs):
        form = super(ReplyForm, self).__init__(*args, **kwargs)
        self.status.choices = [
            (s.id, s.status)
            for s in FlicketStatus.query.filter(FlicketStatus.status != "Closed")
        ]
        self.priority.choices = [
            (p.id, p.priority) for p in FlicketPriority.query.all()
        ]

    content = PageDownField(
        lazy_gettext("Reply"),
        validators=[
            DataRequired(),
            Length(
                min=field_size["content_min_length"],
                max=field_size["content_max_length"],
            ),
        ],
    )
    file = FileField(lazy_gettext("Add Files"), render_kw={"multiple": True})
    status = SelectField(
        lazy_gettext("Status"), validators=[DataRequired()], coerce=int
    )
    priority = SelectField(
        lazy_gettext("Priority"), validators=[DataRequired()], coerce=int
    )
    days = DecimalField(lazy_gettext("days"), default=0)
    submit = SubmitField(lazy_gettext("reply"), render_kw=form_class_button)
    submit_close = SubmitField(
        lazy_gettext("reply and close"), render_kw=form_danger_button
    )


class EditReplyForm(ReplyForm):
    def __init__(self, post_id, *args, **kwargs):
        self.form = super(EditReplyForm, self).__init__(*args, **kwargs)
        self.uploads.choices = generate_choices("Post", id=post_id)

    uploads = MultiCheckBoxField("Label", coerce=int)
    submit = SubmitField(
        lazy_gettext("Edit Reply"),
        render_kw=form_class_button,
        validators=[DataRequired()],
    )


class SearchUserForm(FlaskForm):
    """ Search user. """

    username = StringField(
        lazy_gettext("username"),
        validators=[
            DataRequired(),
            Length(
                min=user_field_size["username_min"], max=user_field_size["username_max"]
            ),
        ],
    )
    submit = SubmitField(lazy_gettext("find user"), render_kw=form_class_button)


class AssignUserForm(SearchUserForm):
    """ Search user. """

    submit = SubmitField(lazy_gettext("assign user"), render_kw=form_class_button)


class SubscribeUser(SearchUserForm):
    """ Search user. """

    submit = SubmitField(lazy_gettext("subscribe user"), render_kw=form_class_button)


class InstituteForm(FlaskForm):
    """ Institute form. """

    institute = StringField(
        lazy_gettext("Institute"),
        validators=[
            DataRequired(),
            Length(
                min=field_size["institute_min_length"],
                max=field_size["institute_max_length"],
            ),
            does_institute_exist,
        ],
    )
    submit = SubmitField(lazy_gettext("add institute"), render_kw=form_class_button)


class DomainForm(FlaskForm):
    """ Domain form. """

    domain = StringField(
        lazy_gettext("Domain"),
        validators=[
            DataRequired(),
            Length(
                min=field_size["domain_min_length"],
                max=field_size["domain_max_length"],
            ),
            does_domain_exist,
        ],
    )
    institute_id = HiddenField("institute_id")
    submit = SubmitField(lazy_gettext("add domain"), render_kw=form_class_button)


class SearchInstituteDomainForm(FlaskForm):
    """ Search institute / domain. """

    institute_domain = StringField(
        lazy_gettext("Institute / Domain"),
        validators=[DataRequired(), does_unique_institute_domain_exist],
    )
    submit = SubmitField(
        lazy_gettext("search institute / domain"), render_kw=form_class_button
    )


class ChangeInstituteDomainForm(SearchInstituteDomainForm):
    """ Change institute / domain. """

    submit = SubmitField(
        lazy_gettext("change institute / domain"), render_kw=form_class_button
    )
