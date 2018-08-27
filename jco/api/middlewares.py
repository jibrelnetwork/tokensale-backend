
class ResponseFormatMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_template_response(self, request, response):
        # print('RESP', type(response), response.data)
        if response.status_code > 299:
            success = False
        else:
            success = True

        if response.status_code > 399:
            data_key = 'errors'
            message_key = 'error'
        else:
            data_key = 'data'
            message_key = 'message'

        data_orig = response.data
        response.data = {'success': success}
        if isinstance(data_orig, dict):
            msg = data_orig.pop('detail', None)
        else:
            msg = None
        if msg:
            response.data[message_key] = msg
        else:
            response.data[data_key] = data_orig
        # print('RESP MOD', type(response), response.data, response.renderer_context)
        response.content = response.rendered_content
        return response
