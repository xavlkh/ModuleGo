begin;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'reviews_module_code_fkey'
          and conrelid = 'public.reviews'::regclass
    ) then
        alter table public.reviews
            add constraint reviews_module_code_fkey
            foreign key (module_code)
            references public.rp_modules (module_code)
            on update cascade
            on delete restrict;
    end if;
end
$$;

create index if not exists reviews_module_code_idx
    on public.reviews (module_code);

commit;
