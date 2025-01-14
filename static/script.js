let map, userMarker, markers = [];

document.addEventListener("DOMContentLoaded", function () {
    const radiusDropdown = document.getElementById("radiusDropdown");
    const radiusInput = document.getElementById("radius");
    const dropdownItems = document.querySelectorAll(".dropdown-item");

    dropdownItems.forEach((item) => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const value = item.getAttribute("data-value");
            const text = item.textContent.trim();

            radiusDropdown.querySelector(".selected-text").textContent = text;
            radiusInput.value = value;

            console.log(`Selected radius: ${value} meters`);
        });
    });
});

function loadGoogleMapsScript(apiKey) {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=initMap`;
    script.async = true;
    document.body.appendChild(script);
}

function initMap() {
    const defaultLocation = { lat: 28.363880, lng: 75.587010 };

    map = new google.maps.Map(document.getElementById("map"), {
        center: defaultLocation,
        zoom: 15,
    });

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude,
                };

                map.setCenter(userLocation);

                userMarker = new google.maps.Marker({
                    position: userLocation,
                    map: map,
                    title: "Your Location",
                    icon: {
                        url: "https://maps.google.com/mapfiles/ms/icons/blue-dot.png",
                    },
                });
            },
            (error) => {
                console.warn("Geolocation failed or was denied. Using default location.");
            }
        );
    } else {
        console.warn("Geolocation is not supported by this browser. Using default location.");
    }

    map.addListener("click", (event) => {
        if (userMarker) {
            userMarker.setMap(null);
        }

        userMarker = new google.maps.Marker({
            position: event.latLng,
            map: map,
            title: "Your Location",
            icon: {
                url: "https://maps.google.com/mapfiles/ms/icons/blue-dot.png",
            },
        });
    });
}

function addMarker(doctor) {
    const infoWindow = new google.maps.InfoWindow();
    const marker = new google.maps.Marker({
        position: { 
            lat: parseFloat(doctor.lat), 
            lng: parseFloat(doctor.lng) 
        },
        map: map,
        icon: {
            url: doctor.profile_image_url, 
            scaledSize: new google.maps.Size(50, 50),
        },
        title: doctor.name,
    });

    markers.push(marker);

    const formattedSpecializations = doctor.specializations
        ? doctor.specializations
              .replace(/,\s*/g, ', ')
              .replace(/\s*\/\s*/g, ' / ')
        : 'Not specified';

    const googleMapsLink = `https://www.google.com/maps?q=${doctor.lat},${doctor.lng}`;

    const formattedSummary = doctor.generated_summary
    ? doctor.generated_summary.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
    : 'No summary available';

    const infoWindowContent = `
        <div style="font-family: Arial, sans-serif; max-width: 250px;">
            <div style="display: flex; align-items: center;">
                <img src="${doctor.profile_image_url}" alt="${doctor.name}" 
                     style="width: 50px; height: 50px; border-radius: 50%; margin-right: 10px;">
                <div>
                    <strong>${doctor.name}</strong><br>
                    ₹${doctor.consultation_fee}
                </div>
            </div>
            <div style="margin-top: 10px;">
                <p style="margin: 0; font-size: 0.9rem; color: #555;">
                    ${formattedSummary ? formattedSummary.slice(0, 100) + '...' : 'No summary available.'}
                    <a href="#" id="read-more-${doctor.id}" style="color: #007bff; text-decoration: none;">Read more</a>
                </p>
            </div>
        </div>
    `;

    marker.addListener('mouseover', () => {
        infoWindow.setContent(infoWindowContent);
        infoWindow.open(map, marker);
    });

    marker.addListener('mouseout', () => {
        infoWindow.close();
    });

    // Event delegation for "Read more"
    google.maps.event.addListener(marker, 'click', () => {
        // Open modal on "Read more" click
        google.maps.event.addListenerOnce(infoWindow, 'domready', () => {
            document.getElementById(`read-more-${doctor.id}`).addEventListener('click', (e) => {
                e.preventDefault();
                openDoctorModal(doctor);
            });
        });
    });
}

function openDoctorModal(doctor) {
    // Create modal overlay
    const modalOverlay = document.createElement('div');
    modalOverlay.id = `modal-overlay-${doctor.id}`;
    modalOverlay.style.position = 'fixed';
    modalOverlay.style.top = '0';
    modalOverlay.style.left = '0';
    modalOverlay.style.width = '100%';
    modalOverlay.style.height = '100%';
    modalOverlay.style.backgroundColor = 'rgba(0, 0, 0, 0.6)';
    modalOverlay.style.display = 'flex';
    modalOverlay.style.alignItems = 'center';
    modalOverlay.style.justifyContent = 'center';
    modalOverlay.style.zIndex = '1000'; // Ensure it's above other elements

    // Create modal content
    const modalContent = document.createElement('div');
    modalContent.style.background = 'white';
    modalContent.style.padding = '20px';
    modalContent.style.borderRadius = '10px';
    modalContent.style.maxWidth = '500px';
    modalContent.style.width = '90%';
    modalContent.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.2)';
    modalContent.style.position = 'relative';
    modalContent.style.fontFamily = 'Arial, sans-serif';

    const formattedSummary = doctor.generated_summary
    ? doctor.generated_summary.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
    : 'No summary available';

    // Modal inner HTML
    modalContent.innerHTML = `
        <button id="close-modal-${doctor.id}" style="
            position: absolute; 
            top: 10px; 
            right: 10px; 
            background: none; 
            border: none; 
            font-size: 1.5rem; 
            cursor: pointer;
        ">&times;</button>
        <div style="text-align: center;">
            <img src="${doctor.profile_image_url}" alt="${doctor.name}" 
                 style="width: 100px; height: 100px; border-radius: 50%; margin-bottom: 10px;">
            <h2>${doctor.name}</h2>
            <p><strong>Fee:</strong> ₹${doctor.consultation_fee}</p>
            <p><strong>Specializations:</strong> ${doctor.specializations || 'Not specified'}</p>
            <p><strong>Address:</strong> ${doctor.address}</p>
            <p><strong>Landmark:</strong> ${doctor.landmark}</p>
            <p><strong>Summary:</strong> ${formattedSummary}</p>
            <a href="${googleMapsLink}" target="_blank" style="color: #007bff; text-decoration: none;">View on Google Maps</a>
        </div>
    `;

    // Append modal content to overlay
    modalOverlay.appendChild(modalContent);
    document.body.appendChild(modalOverlay);

    // Event listener to close modal
    document.getElementById(`close-modal-${doctor.id}`).addEventListener('click', () => {
        document.body.removeChild(modalOverlay);
    });

    // Optional: Close modal when clicking outside the content
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            document.body.removeChild(modalOverlay);
        }
    });
}

function clearMarkers() {
    markers.forEach(marker => marker.setMap(null));
    markers = [];
}


function generateIcons() {
    const icons = [
        "fa-heart", "fa-stethoscope", "fa-temperature-high", "fa-mug-hot"
    ];

    for (let i = 0; i < 50; i++) {
        const iconClass = icons[Math.floor(Math.random() * icons.length)];
        const icon = $('<i>')
            .addClass(`fa ${iconClass} fa-icon`)
            .css({
                top: `${Math.random() * 100}%`,  
                left: `${Math.random() * 100}%`,
                transform: `translate(-50%, -50%)`,
                fontSize: `${Math.random() * 12 + 18}px`,
            });

        $('body').append(icon);
    }
}


$(document).ready(() => {
    console.log("Document is ready");

    fetch('/get-api-key')
        .then(response => response.json())
        .then(data => {
            console.log("API Key fetched:", data.api_key);
            const apiKey = data.api_key;
            loadGoogleMapsScript(apiKey);
        })
        .catch(error => {
            console.error("Error fetching API key:", error);
        });

    $("#doctor-search-form").on("submit", function (e) {
        e.preventDefault();
        console.log("Form submitted");
        const symptoms = $("#symptoms").val();
        const radius = $("#radius").val();

        if (!userMarker) {
            alert("Please pin your location on the map!");
            return;
        }

        const location = userMarker.getPosition();
        const data = {
            latitude: location.lat(),
            longitude: location.lng(),
            radius,
            symptoms,
        };

        console.log("Data to send:", data);

        $(".spinner").show();

        $.ajax({
            url: "http://127.0.0.1:5000/find-doctors-by-symptoms",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify(data),
            success: (response) => {
                console.log("AJAX Success. Response:", response);
                $("#doctor-list").empty();
                clearMarkers();
                $(".spinner").hide();

                if (response.length === 0) {
                    $("#doctor-list").html("<p class='text-center mt-4'>No doctors found in the specified area.</p>");
                    return;
                }

                map.setCenter(location);

                response.forEach((doctor) => {
                    addMarker(doctor);
                    console.log("Doctor data:", doctor);
                    const formattedSummary = doctor.generated_summary
                        ? doctor.generated_summary.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
                        : 'No summary available';
                    const formattedSpecializations = doctor.specializations
                        ? doctor.specializations
                              .replace(/,\s*/g, ', ')
                              .replace(/\s*\/\s*/g, ' / ')
                        : 'Not specified';
                    $("#doctor-list").append(`
                        <div class="col-md-4">
                            <div class="card">
                                <img src="${doctor.profile_image_url}" class="card-img-top" alt="Doctor Image">
                                <div class="card-body">
                                    <h5 class="card-title">${doctor.name}</h5>
                                    <p class="card-text">Specialization: ${formattedSpecializations}</p>
                                    <p class="card-text">Experience: ${doctor.experience}</p>
                                    <p class="card-text">Address: ${doctor.address}</p>
                                    <p class="card-text">Landmark: ${doctor.landmakr}</p>
                                    <p class="card-text">Consultation Fees: ₹${doctor.consultation_fee}</p>
                                    <p class="card-text">Summary: ${formattedSummary}</p>
                                    <a href="${doctor.profile_url}" class="btn btn-custom" target="_blank">View Profile</a>
                                </div>
                            </div>
                        </div>
                    `);
                });

                adjustMapBounds();
            },
            error: (err) => {
                console.error("AJAX Error:", err);
                $(".spinner").hide();
                alert("An error occurred while searching for doctors.");
            },
        });
    });
});
console.log()