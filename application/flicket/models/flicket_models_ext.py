#! usr/bin/python3
# -*- coding: utf-8 -*-
#
# Flicket - copyright Paul Bourne: evereux@gmail.com

import datetime
import os

from application import app, db
from application.flicket.scripts.flicket_upload import UploadAttachment
from application.flicket.models.flicket_models import (
    FlicketTicket,
    FlicketStatus,
    FlicketPriority,
    FlicketRequesterRole,
    FlicketDomain,
    FlicketSubscription,
    FlicketHistory,
    FlicketUploads,
)


class FlicketTicketExt:
    """
    A class to extend the functionality of FlicketTicket.

    Methods aren't included in the FlicketTicket class itself
    due to potential circular import issues with flicket_upload.py
    """

    @staticmethod
    def create_ticket(
        title=None,
        user=None,
        content=None,
        requester=None,
        priority=None,
        requester_role=None,
        domain=None,
        files=None,
        hours=0,
    ):
        """
        :param title:
        :param user:
        :param content:
        :param priority:
        :param requester:
        :param requester_role:
        :param domain:
        :param files:
        :param hours:
        :return:
        """

        ticket_status = FlicketStatus.query.filter_by(status="Open").first()
        ticket_priority = FlicketPriority.query.filter_by(id=int(priority)).first()
        ticket_domain = FlicketDomain.query.filter_by(id=int(domain)).first()
        requester_role = FlicketRequesterRole.query.filter_by(
            id=int(requester_role)
        ).first()

        upload_attachments = UploadAttachment(files)
        if upload_attachments.are_attachments():
            upload_attachments.upload_files()

        # submit ticket data to database
        new_ticket = FlicketTicket(
            title=title,
            date_added=datetime.datetime.now(),
            user=user,
            current_status=ticket_status,
            content=content,
            requester=requester,
            ticket_priority=ticket_priority,
            requester_role=requester_role,
            domain=ticket_domain,
            hours=hours,
        )

        db.session.add(new_ticket)
        # add attachments to the database
        upload_attachments.populate_db(new_ticket)
        # subscribe user to ticket.
        subscribe = FlicketSubscription(user=user, ticket=new_ticket)
        db.session.add(subscribe)

        # add count of 1 to users total posts.
        user.total_posts += 1

        db.session.commit()

        return new_ticket

    @staticmethod
    def edit_ticket(
        ticket=None,
        title=None,
        user=None,
        content=None,
        requester=None,
        priority=None,
        requester_role=None,
        domain=None,
        files=None,
        form_uploads=None,
        hours=None,
    ):
        """

        :param ticket:
        :param title:
        :param user:
        :param content:
        :param priority:
        :param domain:
        :param files:
        :param form_uploads:
        :param hours:
        :return:
        """
        # before we make any changes store the original post content in the history table if it has changed.
        if ticket.modified_id:
            history_id = ticket.modified_id
        else:
            history_id = ticket.started_id

        if ticket.content != content:
            history = FlicketHistory(
                original_content=ticket.content,
                topic=ticket,
                date_modified=datetime.datetime.now(),
                user_id=history_id,
            )
            db.session.add(history)

        # See GH #1
        # if ticket.requester != requester:
        #     history = FlicketHistory(
        #         original_requester=ticket.requester,
        #         topic=ticket,
        #         date_modified=datetime.datetime.now(),
        #         user_id=history_id,
        #     )
        #     db.session.add(history)

        # loop through the selected uploads for deletion.
        if len(form_uploads) > 0:
            for i in form_uploads:
                # get the upload document information from the database.
                query = FlicketUploads.query.filter_by(id=i).first()
                # define the full uploaded filename
                the_file = os.path.join(
                    app.config["ticket_upload_folder"], query.filename
                )

                if os.path.isfile(the_file):
                    # delete the file from the folder
                    os.remove(the_file)

                db.session.delete(query)

        ticket_priority = FlicketPriority.query.filter_by(id=int(priority)).first()
        requester_role = FlicketRequesterRole.query.filter_by(
            id=int(requester_role)
        ).first()
        ticket_domain = FlicketDomain.query.filter_by(id=int(domain)).first()

        ticket.content = content
        ticket.requester = requester
        ticket.title = title
        ticket.modified = user
        ticket.date_modified = datetime.datetime.now()
        ticket.ticket_priority = ticket_priority
        ticket.requester_role = requester_role
        ticket.domain = ticket_domain
        ticket.hours = hours

        files = files
        upload_attachments = UploadAttachment(files)
        if upload_attachments.are_attachments():
            upload_attachments.upload_files()

        # add files to database.
        upload_attachments.populate_db(ticket)

        db.session.commit()

        return ticket.id
