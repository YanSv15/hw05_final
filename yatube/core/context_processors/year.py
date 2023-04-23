from datetime import datetime


def year(request):

    dt = datetime.utcnow().year
    return {
        'year': dt
    }
