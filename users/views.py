from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from users import consumers
from users.forms import UserRegisterForm
import json
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt # To disable CSRF for this API endpoint (use with caution)
from django.views.decorators.http import require_POST # Ensure only POST requests are allowed



# Create your views here.
#
# @login_required
def home_view(request):
    context = {}
    return render(request, 'GUI.html',context)


def SignUpView(request):
    if request.method == 'POST':
        # Use your custom form here
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()  # Saves the user with username, password, AND email
            login(request, user)
            messages.success(request, f"ثبت نام موفق بود! خوش آمدید, {user.username}!")
            return redirect('users:home')
        else:
            messages.error(request, "لطفاً خطاهای زیر را اصلاح کنید.")
    else:
        # Use your custom form here
        form = UserRegisterForm()
        # Render the existing signUp.html template
        # No need to pass page_title if the template is dedicated to signup
    return render(request, 'signUp.html', {'form': form})


def LoginView(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Account was created, welcome {username}')
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                else:
                    return redirect('users:home')
            else:
                messages.error(request, f'Username or password is incorrect')
        else:
            messages.error(request, f'There was an error, please fix the errors')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form, 'title': 'login'})


def LogoutView(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, f'You have been logged out successfully')
    return redirect('users/login')




@csrf_exempt
@require_POST
def receive_packet_view(request):
    """
    Receives packet data from agent and sends it to the WebSocket group.
    """
    try:
        data = json.loads(request.body)
        required_keys = ["source_ip", "destination_ip", "protocol", "timestamp"]
        if not all(key in data for key in required_keys):
            print(f"Received incomplete data: {data}")
            return HttpResponseBadRequest("Missing required keys in JSON payload.")

        # --- Send data via Django Channels to frontend ---
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            consumers.NETWORK_DATA_GROUP_NAME, # Use the group name from consumers.py
            {
                'type': 'network_data_message', # This triggers the method in the consumer
                'message': data                 # The actual data payload
            }
        )
        # ----------------------------------------------------

        # Optionally print confirmation
        # print(f"Relayed Packet Data to WebSocket Group: {data}")

        return JsonResponse({"status": "success", "message": "Data received and relayed"})

    except json.JSONDecodeError:
        print("Received invalid JSON from agent.")
        return HttpResponseBadRequest("Invalid JSON payload.")
    except Exception as e:
        print(f"Error processing/relaying packet data: {e}")
        return JsonResponse({"status": "error", "message": "Internal server error"}, status=500)





@csrf_exempt
@require_POST
def receive_rf_data_view(request):
    print("receive_rf_data_view was hit by agent!") # ADD THIS LINE
    try:
        data = json.loads(request.body)
        print(f"receive_rf_data_view received data: {data}") # ADD THIS LINE
        # Update required_keys for the combined time and frequency domain data
        required_keys = [
            "time_s", "amplitude_v_main", "amplitude_v_secondary",  # Main and Secondary Wave
            "wave_details",  # Contains other wave properties
            "fft_frequencies_hz", "fft_power_dbm", "spectrum_details",  # Frequency domain
            "timestamp"
        ]

        if not all(key in data for key in required_keys):
            missing = [key for key in required_keys if key not in data]
            print(f"RF Receiver: Incomplete RF data. Received keys: {list(data.keys())}. Missing: {missing}")
            return HttpResponseBadRequest(f"Missing required keys in RF JSON payload. Missing: {missing}")

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'rf_spectrum_group',
            {
                'type': 'rf_spectrum_update',
                'message': data
            }
        )
        return JsonResponse({"status": "success", "message": "Simulated RF Data received and relayed"})
    except json.JSONDecodeError:
        print("RF Receiver: Received invalid JSON from agent (Time-Domain data).")
        return HttpResponseBadRequest("Invalid JSON payload for Time-Domain data.")
    except Exception as e:
        print(f"RF Receiver: Error processing/relaying Time-Domain data: {e}")
        return JsonResponse({"status": "error", "message": "Internal server error"}, status=500)

# @login_required # Protect this page
def rf_scanner_view(request):
    return render(request, 'rf_scanner.html')