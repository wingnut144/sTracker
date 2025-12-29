--
-- PostgreSQL database dump
--

\restrict IowMvQDPXk6Hv8ZnQbSQpRPkYy1rlR9Zhx2cS9vo6dW0dryf1Dl0jGHJfne0qut

-- Dumped from database version 15.14
-- Dumped by pg_dump version 15.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: comment; Type: TABLE; Schema: public; Owner: intimateuser
--

CREATE TABLE public.comment (
    id integer NOT NULL,
    encounter_id integer NOT NULL,
    user_id integer NOT NULL,
    text text NOT NULL,
    rating integer,
    suggestions text,
    created_at timestamp without time zone
);


ALTER TABLE public.comment OWNER TO intimateuser;

--
-- Name: comment_id_seq; Type: SEQUENCE; Schema: public; Owner: intimateuser
--

CREATE SEQUENCE public.comment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.comment_id_seq OWNER TO intimateuser;

--
-- Name: comment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: intimateuser
--

ALTER SEQUENCE public.comment_id_seq OWNED BY public.comment.id;


--
-- Name: custom_icon; Type: TABLE; Schema: public; Owner: intimateuser
--

CREATE TABLE public.custom_icon (
    id integer NOT NULL,
    "position" character varying(50) NOT NULL,
    svg_content text NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.custom_icon OWNER TO intimateuser;

--
-- Name: custom_icon_id_seq; Type: SEQUENCE; Schema: public; Owner: intimateuser
--

CREATE SEQUENCE public.custom_icon_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.custom_icon_id_seq OWNER TO intimateuser;

--
-- Name: custom_icon_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: intimateuser
--

ALTER SEQUENCE public.custom_icon_id_seq OWNED BY public.custom_icon.id;


--
-- Name: encounter; Type: TABLE; Schema: public; Owner: intimateuser
--

CREATE TABLE public.encounter (
    id integer NOT NULL,
    user_id integer NOT NULL,
    date date NOT NULL,
    "time" time without time zone,
    "position" character varying(50) NOT NULL,
    duration integer,
    notes text,
    rating integer,
    created_at timestamp without time zone
);


ALTER TABLE public.encounter OWNER TO intimateuser;

--
-- Name: encounter_id_seq; Type: SEQUENCE; Schema: public; Owner: intimateuser
--

CREATE SEQUENCE public.encounter_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.encounter_id_seq OWNER TO intimateuser;

--
-- Name: encounter_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: intimateuser
--

ALTER SEQUENCE public.encounter_id_seq OWNED BY public.encounter.id;


--
-- Name: notification; Type: TABLE; Schema: public; Owner: intimateuser
--

CREATE TABLE public.notification (
    id integer NOT NULL,
    user_id integer NOT NULL,
    encounter_id integer,
    type character varying(50) NOT NULL,
    message character varying(200) NOT NULL,
    read boolean,
    created_at timestamp without time zone
);


ALTER TABLE public.notification OWNER TO intimateuser;

--
-- Name: notification_id_seq; Type: SEQUENCE; Schema: public; Owner: intimateuser
--

CREATE SEQUENCE public.notification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.notification_id_seq OWNER TO intimateuser;

--
-- Name: notification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: intimateuser
--

ALTER SEQUENCE public.notification_id_seq OWNED BY public.notification.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: intimateuser
--

CREATE TABLE public."user" (
    id integer NOT NULL,
    username character varying(80) NOT NULL,
    password_hash character varying(200) NOT NULL,
    partner_code character varying(50),
    partner_id integer,
    full_name character varying(200),
    phone_number character varying(20),
    private_notes text,
    sms_notifications boolean
);


ALTER TABLE public."user" OWNER TO intimateuser;

--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: intimateuser
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_id_seq OWNER TO intimateuser;

--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: intimateuser
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- Name: comment id; Type: DEFAULT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public.comment ALTER COLUMN id SET DEFAULT nextval('public.comment_id_seq'::regclass);


--
-- Name: custom_icon id; Type: DEFAULT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public.custom_icon ALTER COLUMN id SET DEFAULT nextval('public.custom_icon_id_seq'::regclass);


--
-- Name: encounter id; Type: DEFAULT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public.encounter ALTER COLUMN id SET DEFAULT nextval('public.encounter_id_seq'::regclass);


--
-- Name: notification id; Type: DEFAULT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public.notification ALTER COLUMN id SET DEFAULT nextval('public.notification_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- Data for Name: comment; Type: TABLE DATA; Schema: public; Owner: intimateuser
--

COPY public.comment (id, encounter_id, user_id, text, rating, suggestions, created_at) FROM stdin;
\.


--
-- Data for Name: custom_icon; Type: TABLE DATA; Schema: public; Owner: intimateuser
--

COPY public.custom_icon (id, "position", svg_content, created_at) FROM stdin;
\.


--
-- Data for Name: encounter; Type: TABLE DATA; Schema: public; Owner: intimateuser
--

COPY public.encounter (id, user_id, date, "time", "position", duration, notes, rating, created_at) FROM stdin;
\.


--
-- Data for Name: notification; Type: TABLE DATA; Schema: public; Owner: intimateuser
--

COPY public.notification (id, user_id, encounter_id, type, message, read, created_at) FROM stdin;
\.


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: intimateuser
--

COPY public."user" (id, username, password_hash, partner_code, partner_id, full_name, phone_number, private_notes, sms_notifications) FROM stdin;
1	wingnut144	scrypt:32768:8:1$5NPrEBEHzPcFibTI$b9d76fc1e1a37272965b7bc8b5ed73b3ce1053767596421a8c4faa852d4dd22bf94610eabc8bf590c246500ca04a29f894d95b0430501feb7fdc6dd1c0637ab9	0c515f2856ae99ee	\N	\N	\N	\N	f
\.


--
-- Name: comment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: intimateuser
--

SELECT pg_catalog.setval('public.comment_id_seq', 1, false);


--
-- Name: custom_icon_id_seq; Type: SEQUENCE SET; Schema: public; Owner: intimateuser
--

SELECT pg_catalog.setval('public.custom_icon_id_seq', 1, false);


--
-- Name: encounter_id_seq; Type: SEQUENCE SET; Schema: public; Owner: intimateuser
--

SELECT pg_catalog.setval('public.encounter_id_seq', 1, false);


--
-- Name: notification_id_seq; Type: SEQUENCE SET; Schema: public; Owner: intimateuser
--

SELECT pg_catalog.setval('public.notification_id_seq', 1, false);


--
-- Name: user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: intimateuser
--

SELECT pg_catalog.setval('public.user_id_seq', 1, true);


--
-- Name: comment comment_pkey; Type: CONSTRAINT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public.comment
    ADD CONSTRAINT comment_pkey PRIMARY KEY (id);


--
-- Name: custom_icon custom_icon_pkey; Type: CONSTRAINT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public.custom_icon
    ADD CONSTRAINT custom_icon_pkey PRIMARY KEY (id);


--
-- Name: custom_icon custom_icon_position_key; Type: CONSTRAINT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public.custom_icon
    ADD CONSTRAINT custom_icon_position_key UNIQUE ("position");


--
-- Name: encounter encounter_pkey; Type: CONSTRAINT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public.encounter
    ADD CONSTRAINT encounter_pkey PRIMARY KEY (id);


--
-- Name: notification notification_pkey; Type: CONSTRAINT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public.notification
    ADD CONSTRAINT notification_pkey PRIMARY KEY (id);


--
-- Name: user user_partner_code_key; Type: CONSTRAINT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_partner_code_key UNIQUE (partner_code);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: user user_username_key; Type: CONSTRAINT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_username_key UNIQUE (username);


--
-- Name: comment comment_encounter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public.comment
    ADD CONSTRAINT comment_encounter_id_fkey FOREIGN KEY (encounter_id) REFERENCES public.encounter(id);


--
-- Name: comment comment_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public.comment
    ADD CONSTRAINT comment_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: encounter encounter_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public.encounter
    ADD CONSTRAINT encounter_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: notification notification_encounter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public.notification
    ADD CONSTRAINT notification_encounter_id_fkey FOREIGN KEY (encounter_id) REFERENCES public.encounter(id);


--
-- Name: notification notification_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public.notification
    ADD CONSTRAINT notification_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: user user_partner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: intimateuser
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_partner_id_fkey FOREIGN KEY (partner_id) REFERENCES public."user"(id);


--
-- PostgreSQL database dump complete
--

\unrestrict IowMvQDPXk6Hv8ZnQbSQpRPkYy1rlR9Zhx2cS9vo6dW0dryf1Dl0jGHJfne0qut

