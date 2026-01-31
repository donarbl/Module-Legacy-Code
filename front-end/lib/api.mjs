import {state} from "../index.mjs";
import {handleErrorDialog} from "../components/error.mjs";

// === ABOUT THE STATE
// state gives you these two functions only
// updateState({stateKey: newValues})
// destroyState()

// All you can do in this file, please!
// 1. You can go to the back end and make requests for data
// 2. You can put the response data into state in the right place
// 3. You can handle your errors
// Don't touch any other part of the application with this file

// Helper function for making API requests
async function _apiRequest(endpoint, options = {}) {
  const token = state.token;
  const baseUrl = "http://localhost:3000";

  const defaultOptions = {
    headers: {
      "Content-Type": "application/json",
      ...(token ? {Authorization: `Bearer ${token}`} : {}),
    },
    mode: "cors",
    credentials: "include",
  };

  const fetchOptions = {...defaultOptions, ...options};
  const url = endpoint.startsWith("http") ? endpoint : `${baseUrl}${endpoint}`;

  try {
    const response = await fetch(url, fetchOptions);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const error = new Error(
        errorData.message || `API error: ${response.status}`
      );
      error.status = response.status;

      // Handle auth errors
      if (error.status === 401 || error.status === 403) {
        if (!endpoint.includes("/login") && !endpoint.includes("/register")) {
          state.destroyState();
        }
      }

      // Pass all errors forward to a dialog on the screen
      handleErrorDialog(error);
      throw error;
    }

    const contentType = response.headers.get("content-type");
    return contentType?.includes("application/json")
      ? await response.json()
      : {success: true};
  } catch (error) {
    if (!error.status) {
      // Only handle network errors here, response errors are handled above
      handleErrorDialog(error);
    }
    throw error; // Re-throw so it can be caught by the calling function
  }
}

// Local helper to update a profile in the profiles array
function _updateProfile(username, profileData) {
  const profiles = [...state.profiles];
  const index = profiles.findIndex((p) => p.username === username);

  if (index !== -1) {
    profiles[index] = {...profiles[index], ...profileData};
  } else {
    profiles.push({username, ...profileData});
  }
  state.updateState({profiles});
}

// ====== AUTH methods
async function login(username, password) {
  try {
    const data = await _apiRequest("/login", {
      method: "POST",
      body: JSON.stringify({username, password}),
    });

    if (data.success && data.token) {
      state.updateState({
        token: data.token,
        currentUser: username,
        isLoggedIn: true,
      });
      await Promise.all([getBlooms(), getProfile(username), getWhoToFollow()]);
    }

    return data;
  } catch (error) {
    return {success: false};
  }
}

async function getWhoToFollow() {
  try {
    const usernamesToFollow = await _apiRequest("/suggested-follows/3");

    state.updateState({whoToFollow: usernamesToFollow});

    return usernamesToFollow;
  } catch (error) {
    // Error already handled by _apiRequest
    state.updateState({usernamesToFollow: []});
    return [];
  }
}

async function signup(username, password) {
  try {
    const data = await _apiRequest("/register", {
      method: "POST",
      body: JSON.stringify({username, password}),
    });

    if (data.success && data.token) {
      state.updateState({
        token: data.token,
        currentUser: username,
        isLoggedIn: true,
      });
      await getProfile(username);
    }

    return data;
  } catch (error) {
    return {success: false};
  }
}

function logout() {
  state.destroyState();
  return {success: true};
}

// ===== BLOOM methods
async function getBloom(bloomId) {
  const endpoint = `/bloom/${bloomId}`;
  const bloom = await _apiRequest(endpoint);
  state.updateState({singleBloomToShow: bloom});
  return bloom;
}

async function getBlooms(username) {
  const endpoint = username ? `/blooms/${username}` : "/home";

  try {
    const blooms = await _apiRequest(endpoint);

    if (username) {
      _updateProfile(username, {blooms});
    } else {
      state.updateState({timelineBlooms: blooms});
    }

    return blooms;
  } catch (error) {
    // Error already handled by _apiRequest
    if (username) {
      _updateProfile(username, {blooms: []});
    } else {
      state.updateState({timelineBlooms: []});
    }
    return [];
  }
}

/**
 * Fetches blooms containing a specific hashtag
 */
async function getBloomsByHashtag(hashtag) {
  const tag = hashtag.startsWith("#") ? hashtag.substring(1) : hashtag;
  const endpoint = `/hashtag/${encodeURIComponent(tag)}`;

  try {
    const blooms = await _apiRequest(endpoint);
    state.updateState({
      hashtagBlooms: blooms,
      currentHashtag: `#${tag}`,
    });
    return blooms;
  } catch (error) {
    // Error already handled by _apiRequest
    return {success: false};
  }
}

async function postBloom(content) {
  try {
    const data = await _apiRequest("/bloom", {
      method: "POST",
      body: JSON.stringify({content}),
    });

    if (data.success) {
      await getBlooms();
      await getProfile(state.currentUser);
    }

    return data;
  } catch (error) {
    // Error already handled by _apiRequest
    return {success: false};
  }
}
async function rebloom(bloomId) {
  const endpoint = `/bloom/${bloomId}/rebloom`;

  try {
    const data = await _apiRequest(endpoint, {
      method: "POST",
    });

    if (data.success) {
      // refresh main timeline so the new bloom appears
      await getBlooms();
    }

    return data;
  } catch (error) {
    // Error already handled by _apiRequest
    return { success: false };
  }
}


// ======= USER methods
async function getProfile(username) {
  const endpoint = username ? `/profile/${username}` : "/profile";

  try {
    const profileData = await _apiRequest(endpoint);

    if (username) {
      _updateProfile(username, profileData);
    } else {
      const currentUsername = profileData.username;
      const fullProfileData = await _apiRequest(`/profile/${currentUsername}`);
      _updateProfile(currentUsername, fullProfileData);
      state.updateState({currentUser: currentUsername, isLoggedIn: true});
    }

    return profileData;
  } catch (error) {
    // Error already handled by _apiRequest
    if (!username) {
      state.updateState({isLoggedIn: false, currentUser: null});
    }
    return {success: false};
  }
}

async function followUser(username) {
  try {
    const data = await _apiRequest("/follow", {
      method: "POST",
      body: JSON.stringify({follow_username: username}),
    });

    if (data.success) {
      await Promise.all([
        getProfile(username),
        getProfile(state.currentUser),
        getBlooms(),
      ]);
    }

    return data;
  } catch (error) {
    return {success: false};
  }
}

async function unfollowUser(username) {
  try {
    const data = await _apiRequest("/unfollow", {
      method: "POST",
      body: JSON.stringify({follow_username: username}),
    });

    if (data.success) {
      // Update both the unfollowed user's profile and the current user's profile
      await Promise.all([
        getProfile(username),
        getProfile(state.currentUser),
        getBlooms(),
      ]);
    }

    return data;
  } catch (error) {
    // Error already handled by _apiRequest
    return {success: false};
  }
}

const apiService = {
  // Auth methods
  login,
  signup,
  logout,

  // Bloom methods
  getBloom,
  getBlooms,
  postBloom,
  getBloomsByHashtag,
  rebloom,

  // User methods
  getProfile,
  followUser,
  unfollowUser,
  getWhoToFollow,
};

export {apiService};
