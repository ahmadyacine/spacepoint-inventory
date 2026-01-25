// // frontend/js/api.js
// const API_BASE = ""; // Use relative path for production deployment

// function getToken() {
//     return sessionStorage.getItem("token");
// }

// function getRole() {
//     return sessionStorage.getItem("role");
// }



// function getUsername() {
//     return sessionStorage.getItem("username");
// }

// function getFullName() {
//     // Prefer full_name, fall back to username for safety
//     return sessionStorage.getItem("full_name") || getUsername();
// }

// function getInstructorId() {
//     return sessionStorage.getItem("instructor_id");
// }

// function getUserId() {
//     return sessionStorage.getItem("user_id");
// }

// function setAuth(token, role, username, instructorId = null, userId = null) {
//     sessionStorage.setItem("token", token);
//     sessionStorage.setItem("role", role);
//     sessionStorage.setItem("username", username);
//     if (instructorId) {
//         sessionStorage.setItem("instructor_id", instructorId);
//     }
//     if (userId) {
//         sessionStorage.setItem("user_id", userId);
//     }
// }

// function clearAuth() {
//     sessionStorage.removeItem("token");
//     sessionStorage.removeItem("role");
//     sessionStorage.removeItem("username");
//     sessionStorage.removeItem("instructor_id");
//     sessionStorage.removeItem("user_id");
//     sessionStorage.removeItem("full_name");
// }

// async function apiFetch(path, options = {}) {
//     const token = getToken();
//     const headers = options.headers || {};
//     headers["Content-Type"] = "application/json";
//     if (token) {
//         headers["Authorization"] = "Bearer " + token;
//     }

//     const res = await fetch(API_BASE + path, {
//         ...options,
//         headers,
//     });

//     if (res.status === 401) {
//         // Unauthorized - redirect to login
//         clearAuth();
//         window.location.href = "login.html";
//         throw new Error("Unauthorized");
//     }

//     if (!res.ok) {
//         let msg = "API error";
//         try {
//             const data = await res.json();
//             msg = data.detail || JSON.stringify(data);
//         } catch (e) {
//             // Ignore JSON parsing errors
//         }
//         throw new Error(msg);
//     }

//     return res.json();
// }

// frontend/js/api.js
const API_BASE =
  (window.API_BASE && window.API_BASE.trim()) ||
  (location.hostname === "localhost" || location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : ""); // production: same-origin // Use relative path for production deployment

function getToken() {
    return sessionStorage.getItem("token");
}

function getRole() {
    return sessionStorage.getItem("role");
}

function getUsername() {
    return sessionStorage.getItem("username");
}

function getFullName() {
    // Prefer full_name, fall back to username for safety
    return sessionStorage.getItem("full_name") || getUsername();
}

function getInstructorId() {
    return sessionStorage.getItem("instructor_id");
}

function getUserId() {
    return sessionStorage.getItem("user_id");
}

function setAuth(token, role, username, instructorId = null, userId = null, fullName = null) {
    sessionStorage.setItem("token", token);
    sessionStorage.setItem("role", role);
    sessionStorage.setItem("username", username);

    // NEW: store full_name (or fallback to username)
    sessionStorage.setItem("full_name", fullName || username);

    if (instructorId) {
        sessionStorage.setItem("instructor_id", instructorId);
    }
    if (userId) {
        sessionStorage.setItem("user_id", userId);
    }
}

function clearAuth() {
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("role");
    sessionStorage.removeItem("username");
    sessionStorage.removeItem("instructor_id");
    sessionStorage.removeItem("user_id");
    sessionStorage.removeItem("full_name");
}

async function apiFetch(path, options = {}) {
    const token = getToken();
    const headers = options.headers || {};
    headers["Content-Type"] = "application/json";
    if (token) {
        headers["Authorization"] = "Bearer " + token;
    }

    const res = await fetch(API_BASE + path, {
        ...options,
        headers,
    });

    if (res.status === 401) {
        clearAuth();
        window.location.href = "login.html";
        throw new Error("Unauthorized");
    }

    if (!res.ok) {
        let msg = "API error";
        try {
            const data = await res.json();
            msg = data.detail || JSON.stringify(data);
        } catch (e) {
            // no JSON body
        }
        throw new Error(msg);
    }

    // 👇 IMPORTANT PART
    if (res.status === 204) {
        return null; // no content
    }

    return res.json();
}

