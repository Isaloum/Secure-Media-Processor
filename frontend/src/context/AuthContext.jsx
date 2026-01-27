import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserAttribute,
} from 'amazon-cognito-identity-js';
import config from '../utils/config';

const AuthContext = createContext(null);

// Initialize Cognito User Pool
const userPool = new CognitoUserPool({
  UserPoolId: config.cognito.userPoolId,
  ClientId: config.cognito.clientId,
});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check for existing session on mount
  useEffect(() => {
    const cognitoUser = userPool.getCurrentUser();
    if (cognitoUser) {
      cognitoUser.getSession((err, session) => {
        if (err) {
          setUser(null);
        } else if (session.isValid()) {
          cognitoUser.getUserAttributes((err, attributes) => {
            if (!err && attributes) {
              const userData = {};
              attributes.forEach(attr => {
                userData[attr.Name] = attr.Value;
              });
              setUser({
                username: cognitoUser.getUsername(),
                email: userData.email,
                name: userData.name,
                sub: userData.sub,
                accessToken: session.getAccessToken().getJwtToken(),
                idToken: session.getIdToken().getJwtToken(),
              });
            }
          });
        }
        setLoading(false);
      });
    } else {
      setLoading(false);
    }
  }, []);

  const signUp = async (email, password, name) => {
    return new Promise((resolve, reject) => {
      const attributeList = [
        new CognitoUserAttribute({ Name: 'email', Value: email }),
      ];

      if (name) {
        attributeList.push(new CognitoUserAttribute({ Name: 'name', Value: name }));
      }

      userPool.signUp(email, password, attributeList, null, (err, result) => {
        if (err) {
          setError(err.message);
          reject(err);
        } else {
          resolve(result);
        }
      });
    });
  };

  const confirmSignUp = async (email, code) => {
    return new Promise((resolve, reject) => {
      const cognitoUser = new CognitoUser({
        Username: email,
        Pool: userPool,
      });

      cognitoUser.confirmRegistration(code, true, (err, result) => {
        if (err) {
          setError(err.message);
          reject(err);
        } else {
          resolve(result);
        }
      });
    });
  };

  const signIn = async (email, password) => {
    return new Promise((resolve, reject) => {
      const cognitoUser = new CognitoUser({
        Username: email,
        Pool: userPool,
      });

      const authDetails = new AuthenticationDetails({
        Username: email,
        Password: password,
      });

      cognitoUser.authenticateUser(authDetails, {
        onSuccess: (session) => {
          cognitoUser.getUserAttributes((err, attributes) => {
            const userData = {};
            if (attributes) {
              attributes.forEach(attr => {
                userData[attr.Name] = attr.Value;
              });
            }
            const userInfo = {
              username: cognitoUser.getUsername(),
              email: userData.email || email,
              name: userData.name,
              sub: userData.sub,
              accessToken: session.getAccessToken().getJwtToken(),
              idToken: session.getIdToken().getJwtToken(),
            };
            setUser(userInfo);
            setError(null);
            resolve(userInfo);
          });
        },
        onFailure: (err) => {
          setError(err.message);
          reject(err);
        },
      });
    });
  };

  const signOut = () => {
    const cognitoUser = userPool.getCurrentUser();
    if (cognitoUser) {
      cognitoUser.signOut();
    }
    setUser(null);
  };

  const forgotPassword = async (email) => {
    return new Promise((resolve, reject) => {
      const cognitoUser = new CognitoUser({
        Username: email,
        Pool: userPool,
      });

      cognitoUser.forgotPassword({
        onSuccess: (data) => resolve(data),
        onFailure: (err) => {
          setError(err.message);
          reject(err);
        },
      });
    });
  };

  const resetPassword = async (email, code, newPassword) => {
    return new Promise((resolve, reject) => {
      const cognitoUser = new CognitoUser({
        Username: email,
        Pool: userPool,
      });

      cognitoUser.confirmPassword(code, newPassword, {
        onSuccess: () => resolve(),
        onFailure: (err) => {
          setError(err.message);
          reject(err);
        },
      });
    });
  };

  const getAccessToken = () => {
    return user?.accessToken || null;
  };

  const value = {
    user,
    loading,
    error,
    signUp,
    confirmSignUp,
    signIn,
    signOut,
    forgotPassword,
    resetPassword,
    getAccessToken,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
