import React from "react";
import { useNavigate } from "react-router-dom";
import { KeyRound, ShieldAlert, UserCheck } from "lucide-react";
import { useAuth } from "../auth/AuthProvider";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";

export const LoginPage: React.FC = () => {
  const { loginAsDemoUser } = useAuth();
  const navigate = useNavigate();

  const handleDemoLogin = async (role: string, email: string) => {
    await loginAsDemoUser(role, email);
    navigate("/overview");
  };

  return (
    <div className="min-h-screen bg-background flex flex-col justify-center items-center p-6">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <div className="h-12 w-12 rounded-xl bg-primary text-primary-foreground flex items-center justify-center font-black text-xl mx-auto shadow-md">
            SH
          </div>
          <h1 className="text-2xl font-bold tracking-tight">SentinelHealth</h1>
          <p className="text-xs text-muted-foreground">
            Population & Workforce Health Early Warning Decision Support
          </p>
        </div>

        <Card>
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-base">Sign In to Decision Console</CardTitle>
            <CardDescription className="text-xs">
              Select a pre-configured demo identity or authenticate with Keycloak OIDC.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Button
                variant="default"
                className="w-full justify-start text-xs font-semibold"
                onClick={() => handleDemoLogin("workplace_safety_manager", "safety@demo.local")}
              >
                <UserCheck className="h-4 w-4 mr-2 text-emerald-300" />
                Sign in as Vikram Patel (Safety Manager)
              </Button>

              <Button
                variant="outline"
                className="w-full justify-start text-xs font-semibold"
                onClick={() => handleDemoLogin("public_health_analyst", "analyst@demo.local")}
              >
                <UserCheck className="h-4 w-4 mr-2 text-blue-500" />
                Sign in as Dr. Sharma (Public Health Lead)
              </Button>

              <Button
                variant="outline"
                className="w-full justify-start text-xs font-semibold"
                onClick={() => handleDemoLogin("occupational_health_analyst", "ohanalyst@demo.local")}
              >
                <UserCheck className="h-4 w-4 mr-2 text-purple-500" />
                Sign in as Rajesh Kumar (Occ. Health)
              </Button>

              <Button
                variant="outline"
                className="w-full justify-start text-xs font-semibold"
                onClick={() => handleDemoLogin("privacy_officer", "privacy@demo.local")}
              >
                <UserCheck className="h-4 w-4 mr-2 text-amber-500" />
                Sign in as Privacy Officer
              </Button>
            </div>

            <div className="relative py-2">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground text-[10px]">Or Keycloak OIDC</span>
              </div>
            </div>

            <Button
              variant="secondary"
              className="w-full text-xs font-semibold"
              onClick={() => {
                window.location.href = "http://localhost:8081/realms/sentinelhealth/account";
              }}
            >
              <KeyRound className="h-4 w-4 mr-2" /> Connect via Keycloak Single Sign-On
            </Button>
          </CardContent>
        </Card>

        <div className="text-center text-[11px] text-muted-foreground">
          Demo Mode Active • Asia/Kolkata (UTC+5:30) • PostgreSQL PostGIS RLS
        </div>
      </div>
    </div>
  );
};

