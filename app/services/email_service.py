"""
Email service for sending notifications
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
import logging

from app.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """Email service for sending notifications"""
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_pass = settings.smtp_pass
        self.from_email = settings.from_email
        self.from_name = getattr(settings, 'from_name', 'Agno WorkSphere')
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email"""
        try:
            # Check if SMTP credentials are available
            if not self.smtp_user or not self.smtp_pass:
                logger.info(f"📧 EMAIL (No SMTP Config - Logging Only)")
                logger.info(f"To: {to_email}")
                logger.info(f"Subject: {subject}")
                logger.info(f"Content: {text_content or html_content[:200]}...")
                print(f"\n📧 EMAIL NOT SENT (No SMTP Configuration)")
                print(f"To: {to_email}")
                print(f"Subject: {subject}")
                print(f"Content: {text_content or html_content[:200]}...")
                print("-" * 50)
                return False  # Return False to indicate email wasn't actually sent

            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            # Add text content
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email
            if self.smtp_user and self.smtp_pass:
                context = ssl.create_default_context()
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls(context=context)
                    server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.from_email, to_email, message.as_string())
                
                logger.info(f"Email sent successfully to {to_email}")
                print(f"\n✅ EMAIL SENT SUCCESSFULLY")
                print(f"To: {to_email}")
                print(f"Subject: {subject}")
                print("-" * 50)
                return True
            else:
                logger.warning("SMTP credentials not configured, email not sent")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_welcome_email(
        self,
        user_email: str,
        user_name: str,
        organization_name: str,
        login_url: str = "http://localhost:3000/login"
    ) -> bool:
        """Send welcome email to new user"""
        subject = f"Welcome to {organization_name} - Your Agno WorkSphere Account is Ready!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to Agno WorkSphere</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .features {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .feature {{ margin: 10px 0; padding: 10px; border-left: 4px solid #667eea; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to Agno WorkSphere!</h1>
                    <p>Your project management journey starts here</p>
                </div>
                
                <div class="content">
                    <h2>Hello {user_name}!</h2>
                    
                    <p>Congratulations! You've successfully created your Agno WorkSphere account and you're now the <strong>Owner</strong> of <strong>{organization_name}</strong>.</p>
                    
                    <p>As an organization owner, you have full control over your workspace and can:</p>
                    
                    <div class="features">
                        <div class="feature">
                            <strong>👥 Manage Team Members</strong><br>
                            Invite team members and assign roles (Admin, Member, Viewer)
                        </div>
                        <div class="feature">
                            <strong>📊 Create Projects</strong><br>
                            Set up projects and organize work with Kanban boards
                        </div>
                        <div class="feature">
                            <strong>🔒 Control Access</strong><br>
                            Manage permissions and organization settings
                        </div>
                        <div class="feature">
                            <strong>📈 Track Progress</strong><br>
                            Monitor team activity and project progress
                        </div>
                    </div>
                    
                    <p>Ready to get started? Click the button below to access your dashboard:</p>
                    
                    <div style="text-align: center;">
                        <a href="{login_url}" class="button">Access Your Dashboard</a>
                    </div>
                    
                    <h3>🚀 Next Steps:</h3>
                    <ol>
                        <li><strong>Complete your profile</strong> - Add your avatar and personal information</li>
                        <li><strong>Invite your team</strong> - Add team members to your organization</li>
                        <li><strong>Create your first project</strong> - Start organizing your work</li>
                        <li><strong>Set up Kanban boards</strong> - Visualize your workflow</li>
                    </ol>
                    
                    <p>If you have any questions or need help getting started, don't hesitate to reach out to our support team.</p>
                    
                    <p>Welcome aboard!</p>
                    <p><strong>The Agno WorkSphere Team</strong></p>
                </div>
                
                <div class="footer">
                    <p>This email was sent to {user_email}</p>
                    <p>© 2024 Agno WorkSphere. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Agno WorkSphere!
        
        Hello {user_name}!
        
        Congratulations! You've successfully created your Agno WorkSphere account and you're now the Owner of {organization_name}.
        
        As an organization owner, you have full control over your workspace and can:
        - Manage team members and assign roles
        - Create projects and organize work with Kanban boards
        - Control access and organization settings
        - Track progress and monitor team activity
        
        Ready to get started? Visit: {login_url}
        
        Next Steps:
        1. Complete your profile
        2. Invite your team
        3. Create your first project
        4. Set up Kanban boards
        
        Welcome aboard!
        The Agno WorkSphere Team
        """
        
        return await self.send_email(user_email, subject, html_content, text_content)
    
    async def send_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        organization_name: str,
        role: str,
        invitation_url: str
    ) -> bool:
        """Send invitation email to new team member"""
        subject = f"You're invited to join {organization_name} on Agno WorkSphere"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Team Invitation</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .role-badge {{ background: #e3f2fd; color: #1976d2; padding: 5px 15px; border-radius: 20px; font-weight: bold; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 You're Invited!</h1>
                    <p>Join {organization_name} on Agno WorkSphere</p>
                </div>
                
                <div class="content">
                    <p>Hello!</p>
                    
                    <p><strong>{inviter_name}</strong> has invited you to join <strong>{organization_name}</strong> on Agno WorkSphere as a <span class="role-badge">{role.title()}</span>.</p>
                    
                    <p>Agno WorkSphere is a powerful project management platform that helps teams collaborate effectively and get things done.</p>
                    
                    <div style="text-align: center;">
                        <a href="{invitation_url}" class="button">Accept Invitation</a>
                    </div>
                    
                    <p>If you don't have an account yet, you'll be able to create one when you click the invitation link.</p>
                    
                    <p>Looking forward to having you on the team!</p>
                </div>
                
                <div class="footer">
                    <p>This invitation was sent to {to_email}</p>
                    <p>© 2024 Agno WorkSphere. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, html_content)

    async def send_project_creation_confirmation(
        self,
        owner_email: str,
        owner_name: str,
        project_data: dict,
        organization_name: str
    ) -> bool:
        """Send project creation confirmation email to owner"""
        subject = f"🎉 Project '{project_data.get('name', 'Untitled')}' Created Successfully!"

        # Extract project details
        project_name = project_data.get('name', 'Untitled Project')
        project_description = project_data.get('description', 'No description provided')
        team_size = project_data.get('teamSize', 'Not specified')
        industry = project_data.get('industry', 'Not specified')
        tasks_created = len(project_data.get('tasks', []))
        estimated_duration = project_data.get('estimatedDuration', 'Not specified')
        tech_stack = project_data.get('techStack', {})
        workflow_phases = project_data.get('workflow', {}).get('phases', [])

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Project Created</title>
            <style>
                body {{ 
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    margin: 0; 
                    padding: 0; 
                    background-color: #e6f0fa; 
                    color: #1a2b49; 
                    line-height: 1.6; 
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 20px auto; 
                    background-color: #ffffff; 
                    border-radius: 16px; 
                    overflow: hidden; 
                    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1); 
                }}
                .header {{ 
                    background: linear-gradient(135deg, #3b82f6 0%, #10b981 100%); 
                    color: #ffffff; 
                    padding: 40px 30px; 
                    text-align: center; 
                }}
                .header img {{ 
                    max-width: 160px; 
                    margin-bottom: 20px; 
                }}
                .header h1 {{ 
                    margin: 0; 
                    font-size: 30px; 
                    font-weight: 700; 
                }}
                .header p {{ 
                    margin: 10px 0 0; 
                    font-size: 16px; 
                    opacity: 0.9; 
                }}
                .content {{ 
                    padding: 40px 30px; 
                }}
                .content h2 {{ 
                    font-size: 24px; 
                    font-weight: 600; 
                    margin-bottom: 16px; 
                    color: #1a2b49; 
                }}
                .content p {{ 
                    font-size: 16px; 
                    margin: 0 0 16px; 
                    color: #4b5e7e; 
                }}
                .project-card {{ 
                    background: #f1f5f9; 
                    border-radius: 10px; 
                    padding: 24px; 
                    margin: 20px 0; 
                    border-left: 4px solid #3b82f6; 
                }}
                .detail-item {{ 
                    margin-bottom: 20px; 
                }}
                .detail-label {{ 
                    font-size: 13px; 
                    font-weight: 600; 
                    color: #6b7280; 
                    text-transform: uppercase; 
                    margin-bottom: 6px; 
                }}
                .detail-value {{ 
                    font-size: 15px; 
                    font-weight: 500; 
                    color: #1a2b49; 
                }}
                .tasks-section {{ 
                    background: #e6f0fa; 
                    border-radius: 10px; 
                    padding: 20px; 
                    margin: 20px 0; 
                }}
                .tasks-count {{ 
                    font-size: 28px; 
                    font-weight: 700; 
                    color: #3b82f6; 
                    margin-bottom: 8px; 
                }}
                .workflow-phases {{ 
                    margin: 20px 0; 
                }}
                .phase {{ 
                    background: #ffffff; 
                    padding: 12px 16px; 
                    margin: 10px 0; 
                    border-radius: 8px; 
                    border-left: 3px solid #10b981; 
                    font-size: 14px; 
                    color: #1a2b49; 
                }}
                .tech-stack {{ 
                    display: flex; 
                    flex-wrap: wrap; 
                    gap: 8px; 
                    margin: 12px 0; 
                }}
                .tech-item {{ 
                    background: #3b82f6; 
                    color: #ffffff; 
                    padding: 6px 14px; 
                    border-radius: 16px; 
                    font-size: 13px; 
                    font-weight: 500; 
                }}
                .cta-button {{ 
                    display: inline-block; 
                    background: linear-gradient(135deg, #3b82f6 0%, #10b981 100%); 
                    color: #ffffff !important; 
                    padding: 16px 36px; 
                    text-decoration: none; 
                    border-radius: 10px; 
                    font-weight: 600; 
                    font-size: 16px; 
                    margin: 24px 0; 
                    transition: transform 0.2s ease, box-shadow 0.2s ease; 
                }}
                .cta-button:hover {{ 
                    transform: translateY(-3px); 
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); 
                }}
                .next-steps {{ 
                    background: #f1f5f9; 
                    padding: 24px; 
                    border-radius: 10px; 
                    margin: 20px 0; 
                }}
                .next-steps h3 {{ 
                    font-size: 20px; 
                    font-weight: 600; 
                    margin-bottom: 16px; 
                    color: #1a2b49; 
                }}
                .next-steps ul {{ 
                    margin: 0; 
                    padding-left: 24px; 
                    font-size: 15px; 
                    color: #4b5e7e; 
                }}
                .next-steps li {{ 
                    margin-bottom: 12px; 
                }}
                .footer {{ 
                    background: #e6f0fa; 
                    padding: 24px; 
                    text-align: center; 
                    color: #6b7280; 
                    font-size: 13px; 
                    border-top: 1px solid #d1d9e6; 
                }}
                .footer a {{ 
                    color: #3b82f6; 
                    text-decoration: none; 
                    font-weight: 500; 
                }}
                .footer a:hover {{ 
                    text-decoration: underline; 
                }}
                @media (max-width: 600px) {{ 
                    .container {{ margin: 10px; padding: 15px; }}
                    .header {{ padding: 30px 20px; }}
                    .content {{ padding: 30px 20px; }}
                    .project-card {{ padding: 20px; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="https://via.placeholder.com/160x50.png?text=Agno+WorkSphere" alt="Agno WorkSphere Logo">
                    <h1>🎉 Project Created!</h1>
                    <p>Your AI-powered project is ready to launch!</p>
                </div>
                <div class="content">
                    <p>Hello <strong>{owner_name}</strong>,</p>
                    <p>Congratulations! Your new AI-powered project, <strong>"{project_name}"</strong>, has been successfully created within <strong>{organization_name}</strong>. Our intelligent system has crafted a tailored project structure to help you hit the ground running.</p>
                    
                    <div class="project-card">
                        <h2>Project Snapshot</h2>
                        <div class="detail-item">
                            <div class="detail-label">Description</div>
                            <div class="detail-value">{project_description}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Industry</div>
                            <div class="detail-value">{industry}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Team Size</div>
                            <div class="detail-value">{team_size}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Estimated Duration</div>
                            <div class="detail-value">{estimated_duration}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Tasks Generated</div>
                            <div class="detail-value">{tasks_created} tasks</div>
                        </div>
                    </div>

                    <div class="tasks-section">
                        <h3>📋 AI-Generated Task Structure</h3>
                        <div class="tasks-count">{tasks_created}</div>
                        <p>comprehensive tasks have been automatically generated and organized to streamline your project.</p>
                    </div>

                    {f'''
                    <div class="workflow-phases">
                        <h3>🔄 Project Workflow Phases</h3>
                        {''.join([f'<div class="phase">📌 {phase}</div>' for phase in workflow_phases[:5]])}
                    </div>
                    ''' if workflow_phases else ''}

                    {f'''
                    <div>
                        <h3>🛠️ Recommended Tech Stack</h3>
                        <div class="tech-stack">
                            {''.join([f'<span class="tech-item">{tech}</span>' for tech in list(tech_stack.get('frontend', [])) + list(tech_stack.get('backend', [])) + list(tech_stack.get('database', []))][:8])}
                        </div>
                    </div>
                    ''' if tech_stack else ''}

                    <div style="text-align: center;">
                        <a href="http://localhost:3000/projects" class="cta-button">View Your Project Now</a>
                    </div>

                    <div class="next-steps">
                        <h3>🚀 Next Steps to Success</h3>
                        <ul>
                            <li><strong>Review Tasks</strong> - Fine-tune the AI-generated task breakdown to match your vision.</li>
                            <li><strong>Assign Team Members</strong> - Distribute tasks to your team for efficient collaboration.</li>
                            <li><strong>Set Up Kanban Boards</strong> - Visualize your workflow to keep everything on track.</li>
                            <li><strong>Track Progress</strong> - Monitor milestones and project advancements in real-time.</li>
                        </ul>
                    </div>

                    <p>Our AI has laid the foundation for your project, so you can focus on bringing your ideas to life. Need assistance? Our <a href="mailto:support@agnoworksphere.com">support team</a> is here to help.</p>

                    <p>Happy project managing!</p>
                    <p><strong>The Agno WorkSphere Team</strong></p>
                </div>
                <div class="footer">
                    <p>Sent to {owner_email} | <a href="https://agnoworksphere.com/unsubscribe">Unsubscribe</a></p>
                    <p>&copy; 2025 Agno WorkSphere. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Project Created Successfully!

        Hello {owner_name}!

        Congratulations! Your AI-powered project "{project_name}" has been successfully created in {organization_name}.

        Project Details:
        - Name: {project_name}
        - Description: {project_description}
        - Industry: {industry}
        - Team Size: {team_size}
        - Estimated Duration: {estimated_duration}
        - Tasks Generated: {tasks_created} tasks

        What's Next?
        1. Review the generated tasks
        2. Assign team members
        3. Set up your Kanban board
        4. Track progress

        View your project: http://localhost:3000/projects

        Need help? Contact support@agnoworksphere.com

        Happy project managing!
        The Agno WorkSphere Team
        """

        return await self.send_email(owner_email, subject, html_content, text_content)

    async def send_organization_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        organization_name: str,
        role: str,
        invitation_url: str,
        temp_password: str,
        custom_message: Optional[str] = None
    ) -> bool:
        """Send organization invitation email"""
        subject = f"🏢 You're invited to join {organization_name} organization"

        # Role badge styling
        role_colors = {
            'owner': '#ff6b6b',
            'admin': '#4ecdc4',
            'member': '#45b7d1',
            'viewer': '#95a5a6'
        }
        role_color = role_colors.get(role.lower(), '#45b7d1')

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Organization Invitation</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 28px; font-weight: 300; }}
                .content {{ padding: 40px 30px; }}
                .invitation-card {{ background: #f8f9ff; border-left: 4px solid {role_color}; padding: 20px; margin: 20px 0; border-radius: 8px; }}
                .role-badge {{ display: inline-block; background: {role_color}; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 14px; margin: 10px 0; }}
                .credentials {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; margin: 20px 0; }}
                .footer {{ background: #f1f3f4; padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                .organization-icon {{ font-size: 48px; margin-bottom: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="organization-icon">🏢</div>
                    <h1>Organization Invitation</h1>
                    <p>Join {organization_name} and start collaborating</p>
                </div>

                <div class="content">
                    <div class="invitation-card">
                        <p><strong>{inviter_name}</strong> has invited you to join the <strong>{organization_name}</strong> organization as a:</p>
                        <div class="role-badge">{role.title()}</div>
                        {f'<div style="margin: 15px 0; padding: 15px; background: white; border-radius: 6px; font-style: italic;">"{custom_message}"</div>' if custom_message else ''}
                    </div>

                    <div class="credentials">
                        <h3>🔐 Your Login Credentials</h3>
                        <p><strong>Email:</strong> {to_email}</p>
                        <p><strong>Temporary Password:</strong> <code style="background: #e9ecef; padding: 4px 8px; border-radius: 4px;">{temp_password}</code></p>
                        <p><small>⚠️ Please change your password after your first login for security.</small></p>
                    </div>

                    <div style="text-align: center;">
                        <a href="{invitation_url}" class="button">🚀 Join Organization</a>
                    </div>

                    <h3>🌟 What you'll get access to:</h3>
                    <ul>
                        <li>📊 Organization dashboard and analytics</li>
                        <li>👥 Team collaboration tools</li>
                        <li>📋 Project management features</li>
                        <li>💬 Team communication channels</li>
                        <li>📁 Shared resources and documents</li>
                    </ul>

                    <p>Welcome to the team! We're excited to have you aboard.</p>
                    <p><strong>The Agno WorkSphere Team</strong></p>
                </div>

                <div class="footer">
                    <p>This invitation was sent to {to_email}</p>
                    <p>© 2024 Agno WorkSphere. All rights reserved.</p>
                    <p>Need help? Contact our support team</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        🏢 You're invited to join {organization_name} organization!

        Hello!

        {inviter_name} has invited you to join {organization_name} on Agno WorkSphere as a {role.title()}.
        {f'Message: "{custom_message}"' if custom_message else ''}

        Your login credentials:
        Email: {to_email}
        Temporary Password: {temp_password}

        Accept your invitation: {invitation_url}

        Please change your password after your first login for security.

        Welcome to the team!
        The Agno WorkSphere Team
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_project_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        organization_name: str,
        project_name: str,
        role: str,
        invitation_url: str,
        temp_password: str,
        custom_message: Optional[str] = None
    ) -> bool:
        """Send project-specific invitation email"""
        subject = f"📋 You're invited to collaborate on {project_name} project"

        # Role badge styling
        role_colors = {
            'owner': '#ff6b6b',
            'admin': '#4ecdc4',
            'member': '#45b7d1',
            'viewer': '#95a5a6'
        }
        role_color = role_colors.get(role.lower(), '#45b7d1')

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Project Invitation</title>
            <style>
                body {{ 
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    margin: 0; 
                    padding: 0; 
                    background-color: #e6f0fa; 
                    color: #1a2b49; 
                    line-height: 1.6; 
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 20px auto; 
                    background-color: #ffffff; 
                    border-radius: 16px; 
                    overflow: hidden; 
                    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1); 
                }}
                .header {{ 
                    background: linear-gradient(135deg, #3b82f6 0%, #10b981 100%); 
                    color: #ffffff; 
                    padding: 40px 30px; 
                    text-align: center; 
                }}
                .header img {{ 
                    max-width: 160px; 
                    margin-bottom: 20px; 
                }}
                .header h1 {{ 
                    margin: 0; 
                    font-size: 28px; 
                    font-weight: 700; 
                }}
                .header p {{ 
                    margin: 10px 0 0; 
                    font-size: 16px; 
                    opacity: 0.9; 
                }}
                .content {{ 
                    padding: 40px 30px; 
                }}
                .content p {{ 
                    font-size: 16px; 
                    margin: 0 0 16px; 
                    color: #4b5e7e; 
                }}
                .invitation-card {{ 
                    background: #f1f5f9; 
                    border-radius: 10px; 
                    padding: 20px; 
                    margin: 20px 0; 
                    border-left: 4px solid {role_color}; 
                }}
                .role-badge {{ 
                    display: inline-block; 
                    background: {role_color}; 
                    color: #ffffff; 
                    padding: 6px 14px; 
                    border-radius: 20px; 
                    font-weight: 600; 
                    font-size: 13px; 
                    margin: 10px 0; 
                }}
                .credentials {{ 
                    background: #fff3cd; 
                    border: 1px solid #ffeaa7; 
                    padding: 20px; 
                    border-radius: 10px; 
                    margin: 20px 0; 
                }}
                .cta-button {{ 
                    display: inline-block; 
                    background: linear-gradient(135deg, #3b82f6 0%, #10b981 100%); 
                    color: #ffffff !important; 
                    padding: 16px 36px; 
                    text-decoration: none; 
                    border-radius: 10px; 
                    font-weight: 600; 
                    font-size: 16px; 
                    margin: 24px 0; 
                    transition: transform 0.2s ease, box-shadow 0.2s ease; 
                }}
                .cta-button:hover {{ 
                    transform: translateY(-3px); 
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); 
                }}
                .custom-message {{ 
                    background: #f1f5f9; 
                    padding: 16px; 
                    border-radius: 8px; 
                    border: 1px dashed #d1d9e6; 
                    font-style: italic; 
                    color: #4b5e7e; 
                    margin: 20px 0; 
                }}
                .features {{ 
                    margin: 20px 0; 
                }}
                .feature {{ 
                    display: flex; 
                    align-items: flex-start; 
                    margin-bottom: 16px; 
                    padding: 12px; 
                    background: #ffffff; 
                    border-radius: 8px; 
                    border-left: 3px solid #10b981; 
                }}
                .feature-icon {{ 
                    font-size: 20px; 
                    margin-right: 12px; 
                    color: #10b981; 
                }}
                .feature-text strong {{ 
                    color: #1a2b49; 
                    font-weight: 600; 
                }}
                .feature-text p {{ 
                    margin: 0; 
                    font-size: 14px; 
                    color: #4b5e7e; 
                }}
                .footer {{ 
                    background: #e6f0fa; 
                    padding: 24px; 
                    text-align: center; 
                    color: #6b7280; 
                    font-size: 13px; 
                    border-top: 1px solid #d1d9e6; 
                }}
                .footer a {{ 
                    color: #3b82f6; 
                    text-decoration: none; 
                    font-weight: 500; 
                }}
                .footer a:hover {{ 
                    text-decoration: underline; 
                }}
                @media (max-width: 600px) {{ 
                    .container {{ margin: 10px; padding: 15px; }}
                    .header {{ padding: 30px 20px; }}
                    .content {{ padding: 30px 20px; }}
                    .feature {{ flex-direction: column; align-items: center; text-align: center; }}
                    .feature-icon {{ margin-bottom: 10px; margin-right: 0; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="https://via.placeholder.com/160x50.png?text=Agno+WorkSphere" alt="Agno WorkSphere Logo">
                    <h1>You're Invited to Collaborate! 🚀</h1>
                    <p>Join the {project_name} project and make an impact</p>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p><strong>{inviter_name}</strong> has invited you to join the <strong>{project_name}</strong> project within <strong>{organization_name}</strong> as a <span class="role-badge">{role.title()}</span>.</p>
                    
                    {f'<div class="custom-message"><strong>Message from {inviter_name}:</strong><br>"{custom_message}"</div>' if custom_message else ''}
                    
                    <div class="credentials">
                        <h3>🔐 Your Login Credentials</h3>
                        <p><strong>Email:</strong> {to_email}</p>
                        <p><strong>Temporary Password:</strong> <code style="background: #e9ecef; padding: 4px 8px; border-radius: 4px;">{temp_password}</code></p>
                        <p><small>⚠️ Please change your password after your first login for security.</small></p>
                    </div>

                    <div style="text-align: center;">
                        <a href="{invitation_url}" class="cta-button">Join the Project</a>
                    </div>

                    <p style="text-align: center; font-size: 13px; color: #6b7280; margin-top: 16px;">
                        <small>This link will take you to the project. If you're new to Agno WorkSphere, you'll be prompted to set up your account.</small>
                    </p>

                    <div class="features">
                        <h3>🌟 What You'll Do</h3>
                        <div class="feature">
                            <span class="feature-icon">📊</span>
                            <div class="feature-text">
                                <strong>Track Progress</strong>
                                <p>Monitor project milestones and analytics in real-time.</p>
                            </div>
                        </div>
                        <div class="feature">
                            <span class="feature-icon">✅</span>
                            <div class="feature-text">
                                <strong>Manage Tasks</strong>
                                <p>Create, assign, and track tasks using intuitive Kanban boards.</p>
                            </div>
                        </div>
                        <div class="feature">
                            <span class="feature-icon">💬</span>
                            <div class="feature-text">
                                <strong>Collaborate</strong>
                                <p>Engage with your team through seamless communication tools.</p>
                            </div>
                        </div>
                        <div class="feature">
                            <span class="feature-icon">📁</span>
                            <div class="feature-text">
                                <strong>Share Resources</strong>
                                <p>Access and share project files and documents effortlessly.</p>
                            </div>
                        </div>
                    </div>

                    <p>We're thrilled to have you on board! If you need help, reach out to our <a href="mailto:support@agnoworksphere.com">support team</a>.</p>
                    <p><strong>The Agno WorkSphere Team</strong></p>
                </div>
                <div class="footer">
                    <p>Sent to {to_email} | <a href="https://agnoworksphere.com/unsubscribe">Unsubscribe</a></p>
                    <p>&copy; 2025 Agno WorkSphere. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        📋 You're invited to collaborate on {project_name} project!

        Hello!

        {inviter_name} has invited you to join the {project_name} project in {organization_name} as a {role.title()}.
        {f'Message: "{custom_message}"' if custom_message else ''}

        Your login credentials:
        Email: {to_email}
        Temporary Password: {temp_password}

        Accept your invitation: {invitation_url}

        Please change your password after your first login for security.

        What you'll do:
        - Track project progress and milestones
        - Manage tasks with Kanban boards
        - Collaborate with team members
        - Share project files and resources

        We're excited to have you on board!
        The Agno WorkSphere Team
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_task_assignment_email(
        self,
        to_email: str,
        task_title: str,
        task_description: str,
        assigner_name: str,
        project_name: str,
        due_date: Optional[str] = None,
        priority: str = "medium",
        task_url: str = "http://localhost:3000/tasks"
    ) -> bool:
        """Send task assignment notification email"""
        subject = f"📋 New Task Assigned: {task_title}"

        # Priority styling
        priority_colors = {
            'low': '#95a5a6',
            'medium': '#45b7d1',
            'high': '#f39c12',
            'urgent': '#e74c3c'
        }
        priority_color = priority_colors.get(priority.lower(), '#45b7d1')

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Task Assignment</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .task-card {{ background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid {priority_color}; }}
                .priority-badge {{ display: inline-block; background: {priority_color}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; text-transform: uppercase; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 20px 0; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #6c757d; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 New Task Assigned</h1>
                    <p>You have a new task to work on</p>
                </div>

                <div class="content">
                    <p>Hi there!</p>
                    <p><strong>{assigner_name}</strong> has assigned you a new task in the <strong>{project_name}</strong> project.</p>

                    <div class="task-card">
                        <h3>{task_title}</h3>
                        <div class="priority-badge">{priority.title()} Priority</div>
                        {f'<p><strong>Description:</strong> {task_description}</p>' if task_description else ''}
                        {f'<p><strong>Due Date:</strong> {due_date}</p>' if due_date else ''}
                    </div>

                    <a href="{task_url}" class="button">View Task Details</a>

                    <p>Ready to get started? Click the button above to view the full task details and begin working.</p>
                </div>

                <div class="footer">
                    <p>This is an automated notification from Agno WorkSphere</p>
                    <p>Need help? Contact support@agnoworksphere.com</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        New Task Assigned: {task_title}

        {assigner_name} has assigned you a new task in the {project_name} project.

        Task: {task_title}
        Priority: {priority.title()}
        {f'Description: {task_description}' if task_description else ''}
        {f'Due Date: {due_date}' if due_date else ''}

        View task details: {task_url}

        Ready to get started!
        The Agno WorkSphere Team
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_comment_notification_email(
        self,
        to_email: str,
        commenter_name: str,
        task_title: str,
        comment_content: str,
        project_name: str,
        task_url: str = "http://localhost:3000/tasks"
    ) -> bool:
        """Send comment notification email"""
        subject = f"💬 New Comment on {task_title}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>New Comment</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; }}
                .header {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .comment-card {{ background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #28a745; }}
                .button {{ display: inline-block; background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 20px 0; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #6c757d; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💬 New Comment</h1>
                    <p>Someone commented on your task</p>
                </div>

                <div class="content">
                    <p>Hi there!</p>
                    <p><strong>{commenter_name}</strong> left a comment on the task <strong>"{task_title}"</strong> in the <strong>{project_name}</strong> project.</p>

                    <div class="comment-card">
                        <p><strong>{commenter_name} commented:</strong></p>
                        <p>"{comment_content}"</p>
                    </div>

                    <a href="{task_url}" class="button">View Task & Reply</a>

                    <p>Click the button above to view the full conversation and respond if needed.</p>
                </div>

                <div class="footer">
                    <p>This is an automated notification from Agno WorkSphere</p>
                    <p>Need help? Contact support@agnoworksphere.com</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        New Comment on {task_title}

        {commenter_name} left a comment on the task "{task_title}" in the {project_name} project.

        Comment: "{comment_content}"

        View task and reply: {task_url}

        Stay connected with your team!
        The Agno WorkSphere Team
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_board_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        organization_name: str,
        project_name: str,
        board_name: str,
        role: str,
        invitation_url: str,
        temp_password: str,
        custom_message: Optional[str] = None
    ) -> bool:
        """Send board-specific invitation email"""
        subject = f"📋 You're invited to collaborate on {board_name} board"

        # Role badge styling
        role_colors = {
            'owner': '#ff6b6b',
            'admin': '#4ecdc4',
            'member': '#45b7d1',
            'viewer': '#95a5a6'
        }
        role_color = role_colors.get(role.lower(), '#45b7d1')

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Board Invitation</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 28px; font-weight: 300; }}
                .content {{ padding: 40px 30px; }}
                .invitation-card {{ background: #f8f9ff; border-left: 4px solid {role_color}; padding: 20px; margin: 20px 0; border-radius: 8px; }}
                .role-badge {{ display: inline-block; background: {role_color}; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 14px; margin: 10px 0; }}
                .credentials {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; margin: 20px 0; }}
                .footer {{ background: #f1f3f4; padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                .board-icon {{ font-size: 48px; margin-bottom: 10px; }}
                .kanban-preview {{ display: flex; gap: 10px; margin: 20px 0; }}
                .kanban-column {{ background: #e9ecef; padding: 10px; border-radius: 6px; flex: 1; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="board-icon">📋</div>
                    <h1>Board Invitation</h1>
                    <p>Join {board_name} and manage tasks together</p>
                </div>

                <div class="content">
                    <div class="invitation-card">
                        <p><strong>{inviter_name}</strong> has invited you to collaborate on the <strong>{board_name}</strong> board as a:</p>
                        <div class="role-badge">{role.title()}</div>
                        <p><strong>Project:</strong> {project_name}</p>
                        <p><strong>Organization:</strong> {organization_name}</p>
                        {f'<div style="margin: 15px 0; padding: 15px; background: white; border-radius: 6px; font-style: italic;">"{custom_message}"</div>' if custom_message else ''}
                    </div>

                    <div class="kanban-preview">
                        <div class="kanban-column">📝 To Do</div>
                        <div class="kanban-column">🔄 In Progress</div>
                        <div class="kanban-column">✅ Done</div>
                    </div>

                    <div class="credentials">
                        <h3>🔐 Your Login Credentials</h3>
                        <p><strong>Email:</strong> {to_email}</p>
                        <p><strong>Temporary Password:</strong> <code style="background: #e9ecef; padding: 4px 8px; border-radius: 4px;">{temp_password}</code></p>
                        <p><small>⚠️ Please change your password after your first login for security.</small></p>
                    </div>

                    <div style="text-align: center;">
                        <a href="{invitation_url}" class="button">🚀 Join Board</a>
                    </div>

                    <h3>🎯 What you'll be able to do:</h3>
                    <ul>
                        <li>📋 View and manage board cards</li>
                        <li>✅ Create and assign tasks</li>
                        <li>🔄 Move cards between columns</li>
                        <li>💬 Comment and collaborate on tasks</li>
                        <li>📎 Attach files and resources</li>
                        <li>⏰ Set due dates and priorities</li>
                        <li>📊 Track board progress and metrics</li>
                    </ul>

                    <p>Ready to organize and get things done! We're excited to have you aboard.</p>
                    <p><strong>The Agno WorkSphere Team</strong></p>
                </div>

                <div class="footer">
                    <p>This invitation was sent to {to_email}</p>
                    <p>© 2024 Agno WorkSphere. All rights reserved.</p>
                    <p>Need help? Contact our support team</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        📋 You're invited to collaborate on {board_name} board!

        Hello!

        {inviter_name} has invited you to collaborate on the {board_name} board in the {project_name} project as a {role.title()}.

        Project: {project_name}
        Organization: {organization_name}
        {f'Message: "{custom_message}"' if custom_message else ''}

        Your login credentials:
        Email: {to_email}
        Temporary Password: {temp_password}

        Accept your invitation: {invitation_url}

        Please change your password after your first login for security.

        Ready to organize and get things done!
        The Agno WorkSphere Team
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_enhanced_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        organization_name: str,
        role: str,
        invitation_url: str,
        temp_password: str,
        project_name: Optional[str] = None,
        board_name: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> bool:
        """Send enhanced invitation email with automatic template selection using new templates"""
        try:
            from app.templates.email_templates import (
                get_organization_invitation_email,
                get_project_invitation_email,
                get_board_invitation_email
            )

            # Determine which template to use based on context
            if board_name and project_name:
                # Board invitation
                subject = f"📋 You're invited to collaborate on {board_name} board"
                html_content, text_content = get_board_invitation_email(
                    inviter_name, organization_name, project_name, board_name,
                    role, to_email, temp_password, invitation_url, custom_message
                )
            elif project_name:
                # Project invitation
                subject = f"📋 You're invited to collaborate on {project_name} project"
                html_content, text_content = get_project_invitation_email(
                    inviter_name, organization_name, project_name, role,
                    to_email, temp_password, invitation_url, custom_message
                )
            else:
                # Organization invitation
                subject = f"🏢 You're invited to join {organization_name} organization"
                html_content, text_content = get_organization_invitation_email(
                    inviter_name, organization_name, role, to_email,
                    temp_password, invitation_url, custom_message
                )

            return await self.send_email(to_email, subject, html_content, text_content)

        except Exception as e:
            logger.error(f"Failed to send enhanced invitation email: {str(e)}")
            # Fallback to original method
            if board_name and project_name:
                return await self.send_board_invitation_email(
                    to_email, inviter_name, organization_name, project_name,
                    board_name, role, invitation_url, temp_password, custom_message
                )
            elif project_name:
                return await self.send_project_invitation_email(
                    to_email, inviter_name, organization_name, project_name,
                    role, invitation_url, temp_password, custom_message
                )
            else:
                return await self.send_organization_invitation_email(
                    to_email, inviter_name, organization_name, role,
                    invitation_url, temp_password, custom_message
                )

# Global email service instance
email_service = EmailService()

# Convenience functions for backward compatibility
async def send_invitation_email(
    to_email: str,
    inviter_name: str,
    organization_name: str,
    role: str,
    invitation_url: str
) -> bool:
    """Send invitation email to new team member"""
    return await email_service.send_invitation_email(
        to_email, inviter_name, organization_name, role, invitation_url
    )

async def send_welcome_email(
    user_email: str,
    user_name: str,
    organization_name: str,
    login_url: str = "http://localhost:3000/login"
) -> bool:
    """Send welcome email to new user"""
    return await email_service.send_welcome_email(
        user_email, user_name, organization_name, login_url
    )

async def send_project_creation_confirmation(
    owner_email: str,
    owner_name: str,
    project_data: dict,
    organization_name: str
) -> bool:
    """Send project creation confirmation email to owner"""
    return await email_service.send_project_creation_confirmation(
        owner_email, owner_name, project_data, organization_name
    )