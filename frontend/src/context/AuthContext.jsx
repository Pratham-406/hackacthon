import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  auth,
  db,
  googleProvider,
  isFirebaseConfigured,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  sendPasswordResetEmail,
  updateProfile,
  onAuthStateChanged,
  doc,
  setDoc,
  getDoc,
  serverTimestamp
} from '../firebase';

const AuthContext = createContext({
  user: null,
  userProfile: null,
  loading: true,
  isFirebaseConfigured: false,
  login: async () => {},
  signup: async () => {},
  loginWithGoogle: async () => {},
  resetPassword: async () => {},
  logout: async () => {},
  getIdToken: async () => null,
  refreshProfile: async () => {}
});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  // Fetch or create Firestore user profile doc
  const fetchUserProfile = async (firebaseUser, defaultRole = 'passenger') => {
    if (!db || !firebaseUser) return null;
    try {
      const userDocRef = doc(db, 'users', firebaseUser.uid);
      const docSnap = await getDoc(userDocRef);
      if (docSnap.exists()) {
        const data = docSnap.data();
        setUserProfile(data);
        return data;
      } else {
        // First-time document creation (e.g. Google Sign-In)
        const newProfile = {
          uid: firebaseUser.uid,
          fullName: firebaseUser.displayName || 'SmartPool User',
          email: firebaseUser.email || '',
          phone: firebaseUser.phoneNumber || '',
          role: defaultRole,
          provider: firebaseUser.providerData?.[0]?.providerId || 'google',
          createdAt: serverTimestamp(),
          updatedAt: serverTimestamp()
        };
        await setDoc(userDocRef, newProfile);
        
        // If driver role, create corresponding driver record
        if (defaultRole === 'driver') {
          const driverDocRef = doc(db, 'drivers', firebaseUser.uid);
          await setDoc(driverDocRef, {
            userId: firebaseUser.uid,
            fullName: newProfile.fullName,
            phone: newProfile.phone,
            vehicleNumber: 'MH-14-SP-2026',
            vehicleType: 'Sedan (4 Seater)',
            totalSeats: 4,
            availableSeats: 4,
            availabilityStatus: 'active',
            createdAt: serverTimestamp(),
            updatedAt: serverTimestamp()
          });
        }

        setUserProfile(newProfile);
        return newProfile;
      }
    } catch (err) {
      console.warn('Error fetching Firestore user profile:', err);
      // Fallback in-memory profile representation from Auth object
      const fallbackProfile = {
        uid: firebaseUser.uid,
        fullName: firebaseUser.displayName || 'SmartPool User',
        email: firebaseUser.email || '',
        phone: firebaseUser.phoneNumber || '',
        role: defaultRole,
        provider: 'firebase'
      };
      setUserProfile(fallbackProfile);
      return fallbackProfile;
    }
  };

  useEffect(() => {
    if (!isFirebaseConfigured || !auth) {
      setLoading(false);
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        await fetchUserProfile(currentUser);
      } else {
        setUserProfile(null);
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const signup = async (email, password, fullName, role = 'passenger', phone = '') => {
    if (!auth) throw new Error('Firebase Auth is not initialized. Please configure your .env file.');
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    const createdUser = userCredential.user;

    // Update Firebase Auth profile displayName
    if (fullName) {
      try {
        await updateProfile(createdUser, { displayName: fullName });
      } catch (e) {
        console.warn('Could not update displayName:', e);
      }
    }

    // Persist full profile to Firestore users collection
    if (db) {
      const userDocRef = doc(db, 'users', createdUser.uid);
      const profileData = {
        uid: createdUser.uid,
        fullName: fullName || 'SmartPool User',
        email: createdUser.email || email,
        phone: phone || '',
        role: role || 'passenger',
        provider: 'password',
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp()
      };
      await setDoc(userDocRef, profileData);

      // If registered as a driver, register driver record
      if (role === 'driver') {
        const driverDocRef = doc(db, 'drivers', createdUser.uid);
        await setDoc(driverDocRef, {
          userId: createdUser.uid,
          fullName: fullName || 'SmartPool Driver',
          phone: phone || '',
          vehicleNumber: 'MH-14-SP-2026',
          vehicleType: 'Sedan (4 Seater)',
          totalSeats: 4,
          availableSeats: 4,
          availabilityStatus: 'active',
          createdAt: serverTimestamp(),
          updatedAt: serverTimestamp()
        });
      }

      setUserProfile(profileData);
    }

    setUser(createdUser);
    return createdUser;
  };

  const login = async (email, password) => {
    if (!auth) throw new Error('Firebase Auth is not initialized. Please configure your .env file.');
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    setUser(userCredential.user);
    await fetchUserProfile(userCredential.user);
    return userCredential.user;
  };

  const loginWithGoogle = async (role = 'passenger') => {
    if (!auth || !googleProvider) {
      throw new Error('Google Authentication is not configured. Please supply Firebase credentials.');
    }
    const result = await signInWithPopup(auth, googleProvider);
    setUser(result.user);
    await fetchUserProfile(result.user, role);
    return result.user;
  };

  const resetPassword = async (email) => {
    if (!auth) throw new Error('Firebase Auth is not initialized.');
    await sendPasswordResetEmail(auth, email);
  };

  const logout = async () => {
    if (auth) {
      await signOut(auth);
    }
    setUser(null);
    setUserProfile(null);
  };

  const getIdToken = async () => {
    if (!user) return null;
    try {
      return await user.getIdToken();
    } catch (e) {
      console.warn('Failed to retrieve ID token:', e);
      return null;
    }
  };

  const refreshProfile = async () => {
    if (user) {
      await fetchUserProfile(user);
    }
  };

  const value = {
    user,
    userProfile,
    loading,
    isFirebaseConfigured,
    login,
    signup,
    loginWithGoogle,
    resetPassword,
    logout,
    getIdToken,
    refreshProfile
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
