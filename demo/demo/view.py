from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from demo.model import bart_xsum, bart_cnn, bart_base, bart_base_entailment
from django.views.decorators.csrf import csrf_exempt

# Update this to show which models are available in the demo
AVAILABLE_MODELS = [bart_xsum, bart_cnn, bart_base, bart_base_entailment]

AVAILABLE_MODELS_MAPPING = {m.MODEL_NAME: m for m in AVAILABLE_MODELS}
AVAILABLE_MODELS_NAME = [m.MODEL_NAME for m in AVAILABLE_MODELS]


def render_home_page(request):
    """
    Render the homepage for the demo
    :param request:
    :return:
    """
    context = {
        "models": AVAILABLE_MODELS_NAME
    }

    return render(request, 'index.html', context)


@csrf_exempt
def api_produce_summary(request) -> JsonResponse:
    """
    API for using available models to produce summary.

    :param request: a POST request containing the following parameters
        "source": source text
        "model_type": name of the model to used; model names are specified in each model files under model/

    :return: A json response containing the following items
        "summary": produced summary
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    source = request.POST.get('source')
    model_type = request.POST.get('model_type')

    _model = AVAILABLE_MODELS_MAPPING[model_type]

    hypo = _model.produce_summary(source_text=source)

    return JsonResponse({
        'summary': hypo
    })