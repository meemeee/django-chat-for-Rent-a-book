from django.views import generic
from braces.views import LoginRequiredMixin

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse
from . import models
from . import utils
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models import Q, Max
from .utils import get_dialogs_with_user
from django.shortcuts import redirect

from rentabook.models import BookInstance

class DialogListView(LoginRequiredMixin, generic.ListView):
    template_name = 'django_private_chat/dialogs.html'
    model = models.Dialog

    def get_queryset(self):
        dialogs = models.Dialog.objects.filter(Q(owner=self.request.user) | Q(opponent=self.request.user)).annotate(latest_mess=Max('messages__created')).order_by('-latest_mess')
        return dialogs
   
    def get_context_data(self, **kwargs):
        dialogs = models.Dialog.objects.filter(Q(owner=self.request.user) | Q(opponent=self.request.user))
        # Check if user has any existing dialog
        if len(dialogs) == 0:
            pass
        else:
            # Get to the intended opponent, or the first opponent in the list
            context = super().get_context_data()
            if self.kwargs.get('username'):
                # TODO: show alert that user is not found instead of 404
                user = get_object_or_404(get_user_model(), username=self.kwargs.get('username'))
                dialog = utils.get_dialogs_with_user(self.request.user, user)
                if len(dialog) == 0:
                    dialog = models.Dialog.objects.create(owner=self.request.user, opponent=user)
                else:
                    dialog = dialog[0]
                context['active_dialog'] = dialog
            else:
                if self.object_list:
                    context['active_dialog'] = self.object_list[0]
                else: 
                    pass
            if self.request.user == context['active_dialog'].owner:
                context['opponent_username'] = context['active_dialog'].opponent.username
            else:
                context['opponent_username'] = context['active_dialog'].owner.username
            context['ws_server_path'] = '{}://{}:{}/'.format(
                settings.CHAT_WS_SERVER_PROTOCOL,
                settings.CHAT_WS_SERVER_HOST,
                settings.CHAT_WS_SERVER_PORT,
            )
            return context


def addAlert(request, username):
    """Prompt alerts in conversation when redirected from a bookpage"""
    
    # Get book url & name 
    book_url = request.META["HTTP_REFERER"]
    text = book_url.split('/')
    book_id = text[4]
    book_data = BookInstance.objects.filter(pk=book_id)
    book_title = book_data.values_list('title', flat=True)[0]

    # Get users and dialog
    sender = get_user_model().objects.get(username="Bookbot")
    user_owner = get_user_model().objects.get(username=request.user)
    user_opponent = get_user_model().objects.get(username=username)
    dialog = get_dialogs_with_user(user_owner, user_opponent)

    # Save the message
    if len(dialog) > 0:
        msg = models.Message.objects.create(
            dialog=dialog[0],
            sender=sender,
            text=book_title,
            # link to book in Rentabook
            note="/book/{}".format(book_id),
            read=False
        )
    else:
        pass
    return redirect('dialogs_detail', user_opponent) 
